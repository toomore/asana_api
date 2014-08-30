# -*- coding: utf-8 -*-
import urllib
from requests import Request
from requests import Session
from urlparse import urljoin


class AsanaApi(object):
    def __init__(self, api_key):
        self.api_key = api_key
        self.api_url = u'https://app.asana.com/api/1.0/'
        self.session = Session()

    def _requests(self, method, path, params=None):
        path = urljoin(self.api_url, path)
        raw_requests = Request(method, path, auth=(self.api_key, ''),
                params=params)
        return self.session.send(raw_requests.prepare())

    def get(self, *args, **kwargs):
        return self._requests('GET', *args, **kwargs)

    @staticmethod
    def oauth_authorize(client_id, redirect_uri, response_type='code',
            state=None):
        params = {'client_id': client_id,
                  'redirect_uri': redirect_uri,
                  'response_type': response_type}
        if state:
            params.update({'state': state})

        return u'https://app.asana.com/-/oauth_authorize?%s' % urllib.urlencode(params)

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
    print AsanaApi.oauth_authorize('client_id', 'http')