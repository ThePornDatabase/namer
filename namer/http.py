from typing import Optional

import requests
from requests_cache import CachedSession


class Http:
    @staticmethod
    def request(method, url, **kwargs):
        cache_session: Optional[CachedSession] = kwargs.get('cache_session')
        del kwargs['cache_session']

        if kwargs.get("stream", False) or cache_session is None:
            return requests.request(method, url, **kwargs)
        else:
            return cache_session.request(method, url, **kwargs)

    @staticmethod
    def get(url: str, **kwargs):
        return Http.request("GET", url, **kwargs)

    @staticmethod
    def post(url: str, **kwargs):
        return Http.request("POST", url, **kwargs)

    @staticmethod
    def head(url: str, **kwargs):
        return Http.request("HEAD", url, **kwargs)
