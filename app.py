# -*- coding:utf8 -*-
import setting
from asanaapi import AsanaApi
from flask import Flask

app = Flask(__name__)
app.secret_key = setting.SESSION_KEY

@app.route('/')
def home():
    return u'Hello world <a href="%s">Login</a>' % AsanaApi.oauth_authorize(setting.OAUTHID, setting.OAUTHREDIRECT)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
