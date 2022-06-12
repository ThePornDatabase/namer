from typing import Optional

import requests
import requests_cache


class Http:
    @staticmethod
    def request(cache_session: Optional[requests_cache.CachedSession], method, url, **kwargs):
        if kwargs.get("stream", False) or cache_session is None:
            return requests.request(method, url, **kwargs)
        else:
            return cache_session.request(method, url, **kwargs)

    @staticmethod
    def get(cache_session: Optional[requests_cache.CachedSession], url: str, **kwargs):
        if cache_session is None:
            return requests.request("GET", url, **kwargs)
        else:
            return cache_session.request("GET", url, **kwargs)

    @staticmethod
    def post(cache_session: Optional[requests_cache.CachedSession], url: str, **kwargs):
        if cache_session is None:
            return requests.request("POST", url, **kwargs)
        else:
            return cache_session.request("POST", url, **kwargs)

    @staticmethod
    def head(cache_session: Optional[requests_cache.CachedSession], url: str, **kwargs):
        if cache_session is None:
            return requests.request("HEAD", url, **kwargs)
        else:
            return cache_session.request("HEAD", url, **kwargs)
