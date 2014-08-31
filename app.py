# -*- coding:utf8 -*-
import setting
from asanaapi import AsanaApi
from flask import Flask
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for

app = Flask(__name__)
app.secret_key = setting.SESSION_KEY

@app.route('/')
def home():
    return render_template('home.htm', login_url=AsanaApi.oauth_authorize(setting.OAUTHID, setting.OAUTHREDIRECT))

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
        return render_template('user_projects.htm',
                data=asanaapi.get_workspaces()['data'])
    return u'Please login'

@app.route('/user/projects/<workspace_id>')
def projects_tasks(workspace_id):
    if session.get('access_token'):
        asanaapi = AsanaApi(session['access_token'])
        return render_template('user_projects_tasks.htm',
                data=asanaapi.get_workspaces_tasks(workspace_id)['data'],
                workspace_id=workspace_id)
    return u'Please login'

@app.route('/user/tasks/all')
def all_tasks():
    if session.get('access_token'):
        asanaapi = AsanaApi(session['access_token'])
        result = []
        tasks = asanaapi.get_all_my_tasks(7)
        for task in tasks:
            result.append(u'%s name: %s' % (task, tasks[task]))
        return u'<br>'.join(result)
    return u'Please login'

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
