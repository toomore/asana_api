# -*- coding: utf-8 -*-
import urllib
import requests
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

    def get_all_my_tasks(self):
        result = {}
        for project in self.get_workspaces()['data']:
            data = self.get_workspaces_tasks(project['id'])
            if 'data' in data:
                for task in data['data']:
                    result[task['id']] = task['name']
        return result

    def get_workspaces(self):
        return self.get('./workspaces').json()

    def get_workspaces_tasks(self, workspace_id, me=True):
        return self.get('./workspaces/%s/tasks%s' % (workspace_id,
            u'?&assignee=me' if me else u'')).json()

    @staticmethod
    def oauth_authorize(client_id, redirect_uri, response_type='code',
            state=None):
        params = {'client_id': client_id,
                  'redirect_uri': redirect_uri,
                  'response_type': response_type}
        if state:
            params.update({'state': state})

        return u'https://app.asana.com/-/oauth_authorize?%s' % \
                urllib.urlencode(params)

    @staticmethod
    def oauth_token(client_id, client_secret, redirect_uri, code):
        data = {'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'code': code,
                'grant_type': u'authorization_code'}
        result = requests.post(u'https://app.asana.com/-/oauth_token',
                data=data)

        return result.json()

if __name__ == '__main__':
    import setting
    #asana = AsanaApi(setting.API_KEY)
    asana = AsanaApi(u'...')
    params = {'workspace': setting.WORKSPACE,
              'assignee': 'me'}
    ## http://developer.asana.com/documentation/#tasks
    result = asana.get('./tasks', params=params)
    for i in result.json()['data']:
        for ele in i:
            print ele, i[ele],
        print
    print len(result.json()['data'])
    #print AsanaApi.oauth_authorize('client_id', 'http')

    #print AsanaApi.oauth_token(setting.OAUTHID, setting.OAUTHSECRET,
    #        setting.OAUTHREDIRECT, u'...')
