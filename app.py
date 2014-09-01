# -*- coding:utf8 -*-
import setting
from asanaapi import AsanaApi
from datetime import datetime
from datetime import timedelta
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

def pretty_data(data):
    has_working = False
    for task in data:
        task['tags'] = [tag['name'].lower() for tag in task['tags']]
        if 'working' in task['tags']:
            has_working = True

        if 'completed_at' in task and task['completed_at'] is not None:
            task['completed_at'] = AsanaApi.date_decode(task['completed_at'])
        elif 'completed_at' in task and task['completed_at'] is None:
            task['completed_at'] = datetime.now()

        if 'workspace' in task:
            task['workspace'] = task['workspace']['id']

    return {'data': data, 'has_working': has_working}

@app.route('/user/projects/<workspace_id>', defaults={'days': 7})
@app.route('/user/projects/<workspace_id>/<int:days>')
def projects_tasks(workspace_id, days):
    if session.get('access_token'):
        asanaapi = AsanaApi(session['access_token'])
        data = asanaapi.get_workspaces_tasks(workspace_id,
                    completed_since=AsanaApi.date_encode(datetime.now() - timedelta(days=days)),
                    completed=True)['data']
        result = pretty_data(data)
        return render_template('user_projects_tasks.htm',
                data=result['data'], has_working=result['has_working'])
    return u'Please login'

@app.route('/user/tasks/all', defaults={'days': 7})
@app.route('/user/tasks/all/<int:days>')
def all_tasks(days):
    if session.get('access_token'):
        asanaapi = AsanaApi(session['access_token'])
        data = asanaapi.get_all_my_tasks(days)
        result = pretty_data(data)
        return render_template('user_projects_tasks.htm',
                data=result['data'], has_working=result['has_working'])
    return u'Please login'

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
