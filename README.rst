Flaskish
--------

Drop-in replacement for Flask with HTTP API development in mind.

Features:

* ``Flaskish.api`` decorator to define API endpoints::

    from flaskish import Flaskish

    app = Flaskish(__name__)

    @app.api('/api/hello')
    def hello():
        return {'result': 'world'}

    app.run()

* ``Request.response`` attribute to define response headers::

    from flask import request
    from flaskish import Flaskish

    app = Flaskish(__name__)

    @app.api('/api/login')
    def login():
        request.response.set_cookie('auth', 'some-token', httponly=True, max_age=86400*30)
        return {'result': 'ok'}

    app.run()

* Strict slashes are turned off. It's pain to use API which differentiates
  between ``/api`` and ``/api/``.

* No static route by default.

* ``Flaskish.logger`` propagates to root logger. Application logging
  configuration should be in one place without exceptions.

* View functions can have similar names. One have to define explicit view names
  with ``Flaskish.api`` and ``Flaskish.route`` to be able to use
  ``flask.url_for``. You do not need it at first place, and if you do implicit
  view names are brittle anyway.

* ``weight`` arg in ``Flaskish.route`` to be able to define routes priority.

* ``Flaskish.print_routes`` to print routes list.


Installation
------------

::

    pip install flaskish
