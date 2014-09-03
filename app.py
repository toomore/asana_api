# -*- coding:utf8 -*-
import pylibmc
import setting
import time
from asanaapi import AsanaApi
from datetime import datetime
from datetime import timedelta
from flask import Flask
from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from functools import wraps

app = Flask(__name__)
app.secret_key = setting.SESSION_KEY

MEMCACHE = pylibmc.Client(setting.MEMSERVER, binary=True,
        behaviors={"tcp_nodelay": True, "ketama": True})

@app.template_filter('get_project_name')
def get_project_name(workspace_id):
    return MEMCACHE.get('project_name:%s' % str(workspace_id)) or workspace_id

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('expire') and \
                (datetime.fromtimestamp(session['expire']) < datetime.now()):
            flash(u'登入時效過期，請重新登入！')
            return redirect(url_for('home'))
        elif not session.get('access_token'):
            flash(u'請登入！')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    if session.get('access_token'):
        logout()

    return render_template('home.htm', login_url=AsanaApi.oauth_authorize(setting.OAUTHID, setting.OAUTHREDIRECT))

@app.route('/token')
def token():
    code = request.args.get('code')
    result = AsanaApi.oauth_token(setting.OAUTHID, setting.OAUTHSECRET,
            setting.OAUTHREDIRECT, code)

    session['access_token'] = result['access_token']
    session['refresh_token'] = result['refresh_token']
    session['email'] = result['data']['email']
    session['id'] = result['data']['id']
    session['name'] = result['data']['name']
    session['expire'] = int(time.mktime(datetime.now().timetuple()) + int(result['expires_in']))

    #return u'%s' % result
    return redirect(url_for('projects'))

@app.route('/user/projects')
@login_required
def projects():
    result = MEMCACHE.get('user_projects_list:%s' % session['id'])

    if not result:
        asanaapi = AsanaApi(session['access_token'])
        result = asanaapi.get_workspaces()
        MEMCACHE.set('user_projects_list:%s' % session['id'], result, 86400)

    for project in result['data']:
        MEMCACHE.add('project_name:%s' % str(project['id']), project['name'])

    return render_template('user_projects.htm',
            data=result['data'])

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
@login_required
def projects_tasks(workspace_id, days):
    result = MEMCACHE.get('user_projects_tasks:%s:%s:%s' % (session['id'], str(workspace_id), days))

    if not result:
        asanaapi = AsanaApi(session['access_token'])
        data = asanaapi.get_workspaces_tasks(workspace_id,
                    completed_since=AsanaApi.date_encode(datetime.now() - timedelta(days=days)),
                    completed=True)['data']
        result = pretty_data(data)
        MEMCACHE.set('user_projects_tasks:%s:%s:%s' % (session['id'], str(workspace_id), days), result, 60)

    return render_template('user_projects_tasks.htm',
            data=result['data'], has_working=result['has_working'],
            workspace_id=workspace_id, days=days)

@app.route('/user/tasks/all', defaults={'days': 7})
@app.route('/user/tasks/all/<int:days>')
@login_required
def all_tasks(days):
    result = MEMCACHE.get('user_all_tasks:%s:%s' % (session['id'], days))

    if not result:
        asanaapi = AsanaApi(session['access_token'])
        data = asanaapi.get_all_my_tasks(days)
        result = pretty_data(data)
        MEMCACHE.set('user_all_tasks:%s:%s' % (session['id'], days), result, 60)

    return render_template('user_projects_tasks.htm',
            data=result['data'], has_working=result['has_working'],
            is_all=True, days=days)

@app.route('/logout')
def logout():
    for i in ['access_token', 'refresh_token', 'email', 'id', 'name', 'expire']:
        session.pop(i, None)

    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
