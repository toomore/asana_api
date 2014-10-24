# -*- coding:utf8 -*-
import hashlib
import pylibmc
import re
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

@app.template_filter('replace_github_pr')
def replace_github_pr(words):
    results = re.findall(r'\[PR:([0-9,]+)\]', words)
    for result in results:
        r = re.search('(PR:%s)' % result, words)
        if r:
            rstr = []
            for i in result.split(','):
                rstr.append('<a href="%s">%s</a>' % (setting.PR_DEFAULT % i, i))
            words = words[:r.start()] + 'PR:' + ','.join(rstr) + words[r.end():]
    return words

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
    return redirect(url_for('workspaces'))

@app.route('/user/workspaces')
@login_required
def workspaces():
    result = MEMCACHE.get('user_workspaces_list:%s' % session['id'])

    if not result:
        asanaapi = AsanaApi(session['access_token'])
        result = asanaapi.get_workspaces()
        MEMCACHE.set('user_workspaces_list:%s' % session['id'], result, 86400)

    workspaces_projects_data = MEMCACHE.get('user_workspaces_projects:%s' % session['id'])
    if not workspaces_projects_data:
        asanaapi = AsanaApi(session['access_token'])
        workspaces_projects_data = {}
        for workspace in result['data']:
            MEMCACHE.add('workspaces_name:%s' % str(workspace['id']), workspace['name'])
            wp_result = asanaapi.get_workspaces_projects(workspace['id'])

            if 'data' in wp_result:
                workspaces_projects_data[workspace['id']] = wp_result['data']

        MEMCACHE.set('user_workspaces_projects:%s' % session['id'], workspaces_projects_data, 300)

    return render_template('user_workspaces.htm',
            data=result['data'],
            workspaces_projects_data=workspaces_projects_data)

def pretty_data(data):
    has_working = False
    parent_task = {}
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

        if 'parent' in task and task['parent']:
            parent_task.setdefault(task['parent']['id'], {})
            parent_task[task['parent']['id']].setdefault('working', [])
            parent_task[task['parent']['id']].setdefault('completed', [])
            parent_task[task['parent']['id']].setdefault('not_completed', [])

            parent_task[task['parent']['id']]['name'] = task['parent']['name']
            parent_task[task['parent']['id']]['workspace_id'] = task['parent']['workspace']['id']
            parent_task[task['parent']['id']].setdefault('data', [])
            parent_task[task['parent']['id']]['data'].append(task)

            if task['completed']:
                parent_task[task['parent']['id']]['completed'].append(task)
            elif 'working' in task['tags']:
                parent_task[task['parent']['id']]['working'].append(task)
            else:
                parent_task[task['parent']['id']]['not_completed'].append(task)

    return {'data': data, 'has_working': has_working,
            'parent_task': parent_task}

@app.route('/user/projects/<workspace_id>', defaults={'days': 7})
@app.route('/user/projects/<workspace_id>/<int:days>')
@login_required
def projects_tasks(workspace_id, days):
    cache_key = 'user_projects_tasks:%s:%s:%s' % (session['id'], str(workspace_id), days)
    cache_time = 3600
    hash_cache_key = hashlib.md5(cache_key).hexdigest()
    result = MEMCACHE.get(cache_key)

    if not result:
        asanaapi = AsanaApi(session['access_token'])
        data = asanaapi.get_workspaces_tasks(workspace_id,
                    completed_since=AsanaApi.date_encode(datetime.now() - timedelta(days=days)),
                    completed=True)['data']
        result = pretty_data(data)
        MEMCACHE.set(cache_key, result, cache_time)
        MEMCACHE.set(hash_cache_key,
                (cache_key, url_for('projects_tasks', workspace_id=workspace_id, days=days)),
                cache_time)

    return render_template('user_projects_tasks.htm',
            data=result['data'], has_working=result['has_working'],
            workspace_id=workspace_id, days=days, hash_cache_key=hash_cache_key,
            parent_task=result['parent_task'])

@app.route('/user/tasks/all', defaults={'days': 7})
@app.route('/user/tasks/all/<int:days>')
@login_required
def all_tasks(days):
    cache_key = 'user_all_tasks:%s:%s' % (session['id'], days)
    cache_time = 3600
    hash_cache_key = hashlib.md5(cache_key).hexdigest()
    result = MEMCACHE.get(cache_key)

    if not result:
        asanaapi = AsanaApi(session['access_token'])
        data = asanaapi.get_all_my_tasks(days)
        result = pretty_data(data)
        MEMCACHE.set(cache_key, result, cache_time)
        MEMCACHE.set(hash_cache_key, (cache_key, url_for('all_tasks', days=days)), cache_time)

    return render_template('user_projects_tasks.htm',
            data=result['data'], has_working=result['has_working'],
            is_all=True, days=days, hash_cache_key=hash_cache_key,
            parent_task=result['parent_task'])

@app.route('/userinfo')
@login_required
def user_info():
    return render_template('user_info.htm')

@app.route('/cache_stats')
@login_required
def cache_stats():
    return render_template('cache_stats.htm', data=MEMCACHE.get_stats()[0])

@app.route('/cache/flush/<cache_key>')
@login_required
def flush_page_cache(cache_key):
    if cache_key and str(cache_key) in MEMCACHE:
        result = MEMCACHE.get(str(cache_key))
        MEMCACHE.delete(result[0])
        return redirect(result[1])

    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    for i in ['access_token', 'refresh_token', 'email', 'id', 'name', 'expire']:
        session.pop(i, None)

    return redirect(url_for('home'))

@app.route('/follower/w/<workspace_id>/p/<project_id>', defaults={'days': 7})
@app.route('/follower/w/<workspace_id>/p/<project_id>/<int:days>')
def follower_workspace_project(workspace_id, project_id, days=7):
    asanaapi = AsanaApi(session['access_token'])
    #data = asanaapi.get('./workspaces/%s/projects' % workspace_id)
    #list_workspace_id = [i['id'] for i in data.json()['data']]

    result_data = []
    results = asanaapi.get_workspaces_tasks(workspace_id,
            follower=session['id'],
            modified_since=AsanaApi.date_encode(datetime.now() - timedelta(days=days)),
            project_id=project_id)

    project_name = u''
    if results and results.get('data'):
        for result in results['data']:
            if result['assignee'] and int(session['id']) != result['assignee']['id']:
                if session['id'] in [f['id'] for f in result['followers']]:
                    #result_data.append(u'[%s] <a href="https://app.asana.com/0/%s/%s">%s</a> %s' % (result['completed'], project_id, result['id'], result['name'], result['modified_at']))
                    result_data.append(result)
                    project_name = result['projects'][0]['name']

    #return u'%s' % u'<br>'.join(result_data)
    return render_template('follower_workspace_project.htm',
            data=result_data,
            workspace_id=workspace_id,
            project_name=project_name,
            days=days)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
