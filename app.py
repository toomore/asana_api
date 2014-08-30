# -*- coding:utf8 -*-
import setting
from asanaapi import AsanaApi
from flask import Flask
from flask import redirect
from flask import request
from flask import session
from flask import url_for

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

    session['access_token'] = result['access_token']
    session['email'] = result['data']['email']
    session['id'] = result['data']['id']
    session['name'] = result['data']['name']

    #return u'%s' % result
    return redirect(url_for('projects'))

@app.route('/user/projects')
def projects():
    if session.get('access_token'):
        asanaapi = AsanaApi(session['access_token'])
        return u'%s' % asanaapi.get_workspaces()
    return u'Please login'

@app.route('/user/projects/<workspace_id>')
def projects_tasks(workspace_id):
    if session.get('access_token'):
        asanaapi = AsanaApi(session['access_token'])
        result = []
        for i in asanaapi.get_workspaces_tasks(workspace_id)['data']:
            result.append(u'%(id)s name: %(name)s' % i)
        return u'<br>'.join(result)
    return u'Please login'

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
