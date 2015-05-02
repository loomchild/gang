from collections import namedtuple
import requests


def to_object(json):
    if isinstance(json, dict):
        obj = _dict_to_object({k : to_object(v) for (k,v) in json.iteritems()})
    elif isinstance(json, list):
        obj = [to_object(e) for e in json]
    else:
        obj = json
    return obj

def _dict_to_object(d):
    return namedtuple('DictObject', d.keys())(*d.values())


class Api(object):

    def __init__(self, url, params={}, headers={}):
        self.url = url
        self.params = params
        self.headers = headers

    def call(self, method, path, status_codes, **kwargs):
        full_url = self.url + path

        params = {}
        params.update(self.params)
        params.update(kwargs)
        
        headers = self.headers
        
        response = requests.request(method, full_url, params=params, headers=headers)

        if not response.status_code in status_codes:
            raise ExternalApiError("Error calling external API", self.url, 
                    method, path, response.status_code, get_reason(response))

        return response

    def get(self, path, **kwargs):
        r = self.call('GET', path, [200, 404], **kwargs)
        if r.status_code == 404:
            return None
        else:
            return to_object(r.json())
    
    def post(self, path, **kwargs):
        return self.call('POST', path, [200, 201], **kwargs).status_code

    def put(self, path, **kwargs):
        return self.call('PUT', path, [200], **kwargs).status_code
    
    def delete(self, path, **kwargs):
        return self.call('DELETE', [200, 204], path, **kwargs).status_code

    def get_reason(response):
        return response.text


class BountyFundingApi(Api):
    
    def __init__(self, url='http://localhost:8080', token=None):
        super(BountyFundingApi, self).__init__(url, params=dict(token=token))


class GithubApi(Api):
    
    def __init__(self, url='https://api.github.com', token=None):
        super(GithubApi, self).__init__(url, headers=dict(Authorization="token " + token))
    
    def get_reason(response):
        return response.json().get("message")
