# -*- coding: utf-8 -*-
from gevent import monkey
monkey.patch_all()

import gevent
import requests
import time
import urllib
from datetime import datetime
from datetime import timedelta
from gevent.pool import Pool
from requests import Request
from requests import Session
from urlparse import urljoin


class AsanaApi(object):
    def __init__(self, api_key):
        self.api_key = api_key
        self.session = Session()

    def _requests(self, method, path, params=None):
        path = urljoin(u'https://app.asana.com/api/1.0/', path)
        # ----- API token ----- #
        #raw_requests = Request(method, path, auth=(self.api_key, ''),
        #        params=params)

        raw_requests = Request(method, path, params=params)

        # ----- OAUTH token ----- #
        raw_requests.headers['Authorization'] = 'Bearer %s' % self.api_key

        return self.session.send(raw_requests.prepare())

    def get(self, *args, **kwargs):
        return self._requests('GET', *args, **kwargs)

    #def get_all_my_tasks(self, delta=None):
    #    result = []
    #    for project in self.get_workspaces()['data']:
    #        if delta:
    #            data = self.get_workspaces_tasks(project['id'],
    #                    completed_since=self.date_encode(datetime.now() - timedelta(days=delta)),
    #                    completed=True)
    #        else:
    #            data = self.get_workspaces_tasks(project['id'])
    #        result.extend(data['data'])
    #    return result

    def gevent_get_data(self, delta, project_id):
        if delta:
            data = self.get_workspaces_tasks(project_id,
                    completed_since=self.date_encode(datetime.now() - timedelta(days=delta)),
                    completed=True)
        else:
            data = self.get_workspaces_tasks(project['id'])

        return data['data']

    def get_all_my_tasks(self, delta=None, pool_nums=4):
        gevent_spawn_list = []
        pool = Pool(pool_nums)

        for project in self.get_workspaces()['data']:
            gevent_spawn_list.append(pool.spawn(self.gevent_get_data, delta,
                project['id']))

        gevent.joinall(gevent_spawn_list)

        result = []
        for i in gevent_spawn_list:
            result.extend(i.value)

        return result

    def get_workspaces(self):
        return self.get('./workspaces').json()

    def get_workspaces_tasks(self, workspace_id, assignee='me', completed_since=None,
            completed=None, follower=None, project_id=None):
        params = {}
        if assignee and not follower:
            params.update({'assignee': assignee})
        if follower:
            params.update({'follower': follower})
        if project_id:
            params.update({'project': project_id})
        if completed_since:
            params.update({'completed_since': completed_since})
        if completed is not None:
            params.update({'completed': completed})

        params.update({'opt_fields': "name,completed,tags.name,completed_at,workspace.name,parent.name,parent.workspace,followers,assignee.name"})

        return self.get('./workspaces/%s/tasks' % workspace_id, params=params).json()

    @staticmethod
    def oauth_authorize(client_id, redirect_uri, response_type='code',
            state=None):
        ''' example: https://github.com/Asana/oauth-examples '''
        params = {'client_id': client_id,
                  'redirect_uri': redirect_uri,
                  'response_type': response_type}
        if state:
            params.update({'state': state})

        return u'https://app.asana.com/-/oauth_authorize?%s' % \
                urllib.urlencode(params)

    @staticmethod
    def oauth_token(client_id, client_secret, redirect_uri, code=None,
            refresh_token=None, grant_type='authorization_code'):

        data = {'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'grant_type': grant_type}

        if grant_type == 'authorization_code':
            data.update({'code': code})
        elif grant_type == 'refresh_token':
            data.update({'refresh_token': refresh_token})
        else:
            raise

        result = requests.post(u'https://app.asana.com/-/oauth_token',
                data=data)

        return result.json()

    @staticmethod
    def date_encode(date):
        return date.strftime('%Y-%m-%dT%H:%M:%SZ')

    @staticmethod
    def date_decode(datestr):
        return datetime.strptime(datestr, '%Y-%m-%dT%H:%M:%S.%fZ')

if __name__ == '__main__':
    import setting
    #asana = AsanaApi(setting.API_KEY)
    #params = {'workspace': setting.WORKSPACE,
    #          'assignee': 'me'}
    ### http://developer.asana.com/documentation/#tasks
    #result = asana.get('./tasks', params=params)
    #for i in result.json()['data']:
    #    for ele in i:
    #        print ele, i[ele],
    #    print
    #print len(result.json()['data'])
    #print AsanaApi.oauth_authorize('client_id', 'http')

    #print AsanaApi.oauth_token(setting.OAUTHID, setting.OAUTHSECRET,
    #        setting.OAUTHREDIRECT, refresh_token=u'...', grant_type='refresh_token')
    #print AsanaApi.date_decode(AsanaApi.date_encode())
