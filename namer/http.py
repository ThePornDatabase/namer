from typing import Optional

import requests
from requests_cache import CachedSession


class Http:
    @staticmethod
    def request(method, url, cache_session: Optional[CachedSession] = None, **kwargs):
        if kwargs.get("stream", False) or cache_session is None:
            return requests.request(method, url, **kwargs)
        else:
            return cache_session.request(method, url, **kwargs)

    @staticmethod
    def get(url: str, cache_session: Optional[CachedSession] = None, **kwargs):
        return Http.request("GET", url, cache_session, **kwargs)

    @staticmethod
    def post(url: str, cache_session: Optional[CachedSession] = None, **kwargs):
        return Http.request("POST", url, cache_session, **kwargs)

    @staticmethod
    def head(url: str, cache_session: Optional[CachedSession] = None, **kwargs):
        return Http.request("HEAD", url, cache_session, **kwargs)
