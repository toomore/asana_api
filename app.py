# -*- coding:utf8 -*-
import setting
from asanaapi import AsanaApi
from flask import Flask
from flask import request

app = Flask(__name__)
app.secret_key = setting.SESSION_KEY

@app.route('/')
def home():
    return u'Hello world <a href="%s">Login</a>' % AsanaApi.oauth_authorize(setting.OAUTHID, setting.OAUTHREDIRECT)

@app.route('/token')
def token():
    code = request.args.get('code')
    result = AsanaApi.oauth_token(setting.OAUTHID, setting.OAUTHSECRET,
            setting.OAUTHREDIRECT, code)
    return u'%s' % result

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
