from flask import request
from flaskish import Flaskish

app = Flaskish(__name__)

@app.api('/api/hello')
def hello():
    return {'result': 'world'}

@app.api('/api/login')
def login():
    request.response.set_cookie('auth', 'some-token', httponly=True, max_age=86400*30)
    return {'result': 'ok'}

app.run()
