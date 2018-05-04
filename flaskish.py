# Copyright (c) 2018 Anton Bobrov
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from __future__ import print_function

import logging
import sys
from functools import wraps

from flask import Flask as _Flask
from flask.globals import _request_ctx_stack
from werkzeug.datastructures import Headers
from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Response


try:
    import ujson as json
except ImportError:
    import json

_Request = _Flask.request_class


class cached_property(object):
    def __init__(self, func):
        self.__doc__ = getattr(func, '__doc__')
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


class ApiError(Exception):
    """Base API error exception

    You can subclass it and define own ``to_json`` behaviour.
    The only mandatory property for children is ``status_code``.
    """
    status_code = 500
    error = 'internal-error'

    def __init__(self, error=None, status_code=None, **kwargs):
        self.status_code = status_code or self.status_code
        self.error = error or self.error
        self.details = kwargs

    def to_json(self):
        data = {'error': self.error}
        self.details and data.update(self.details)
        return data


class Request(_Request):
    """Request wrapper

    Allows to fiddle with response headers via ``request.response``
    attribute.
    """
    def __init__(self, *args, **kwargs):
        _Request.__init__(self, *args, **kwargs)
        self._response = None

    @cached_property
    def response(self):
        self._response = HeaderResponse()
        return self._response

    def process_response(self, response):
        headers = self._response and self._response.headers
        if headers:
            response.headers._list.extend(headers)
        return response


class HeaderResponse(Response):
    def __init__(self):
        # Skip Response.__init__ for optimization sake.
        self.headers = Headers()


class Flaskish(_Flask):
    """Drop-in replacement for Flask with HTTP API development in mind

    Main changes:

    * Strict slashes are turned off.
    * ``Flaskish.logger`` propagates to root.
    * View functions can have similar names.
    * ``weight`` arg in ``self.route`` to be able to define routes priority.
    * ``Flaskish.api`` decorator to define API endpoints.
    * ``Flaskish.print_routes`` to print routes list.
    """
    request_class = Request
    error_class = ApiError

    def __init__(self, *args, static_folder=None, **kwargs):
        _Flask.__init__(self, *args, static_folder=static_folder, **kwargs)
        self.url_map.strict_slashes = False
        self.endpoint_counter = 0
        self._logger = logging.getLogger(self.logger_name)

    def route(self, rule, endpoint=None, weight=None, **options):
        if weight is not None:
            weight = False, -9999, weight

        def decorator(func):
            lendpoint = endpoint
            if not lendpoint:
                lendpoint = '{}_{}'.format(func.__name__, self.endpoint_counter)
                self.endpoint_counter += 1
            self.add_url_rule(rule, lendpoint, func, **options)
            if weight:
                self.url_map._rules[-1].match_compare_key = lambda: weight
            return func
        return decorator

    def api(self, *args, **kwargs):
        def decorator(func):
            @wraps(func)
            def inner(*args, **kwargs):
                try:
                    result = func(*args, **kwargs)
                except ApiError as e:
                    result = e
                except HTTPException as e:
                    result = e
                except Exception:
                    self.logger.exception('Unhandled error')
                    result = self.error_class()

                if isinstance(result, Response):
                    return result
                elif isinstance(result, ApiError):
                    code = result.status_code
                    result = result.to_json()
                else:
                    code = 200

                try:
                    response_body = json.dumps(result, ensure_ascii=False)
                except Exception:
                    self.logger.exception('Error serializing response')
                    response_body = json.dumps(self.error_class().to_json(), ensure_ascii=False)
                    code = 500

                return self.response_class(response_body, code, content_type='application/json')
            return self.route(*args, **kwargs)(inner)
        return decorator

    def process_response(self, response):
        response = _request_ctx_stack.top.request.process_response(response)
        return _Flask.process_response(self, response)

    def print_routes(self, sort=False):
        rules = self.url_map.iter_rules()
        if sort:
            rules = sorted(rules, key=lambda r: r.rule)

        for rule in rules:
            func = self.view_functions[rule.endpoint]
            print('{:10} {}\t{}.{}'.format(
                ','.join(rule.methods),
                rule.rule,
                func.__module__,
                func.__name__))


def make_module(name, content):
    pkg, _, mname = name.rpartition('.')
    if pkg:
        __import__(pkg)
    else:
        module = type(sys)(mname)
        module.__dict__.update(content)

    if pkg:
        module.__package__ = pkg
        setattr(sys.modules[pkg], mname, module)

    sys.modules[name] = module


def import_as(name):
    def inner(cls):
        make_module(name, cls.__dict__)
        return cls

    return inner
