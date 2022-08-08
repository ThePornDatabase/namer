from io import BytesIO
from typing import Optional

import requests
from loguru import logger
from requests_cache import CachedSession


class Http:
    @staticmethod
    def request(method, url, **kwargs):
        logger.info(f'Requesting {method} "{url}"')
        cache_session: Optional[CachedSession] = kwargs.get('cache_session')
        if 'cache_session' in kwargs:
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

    @staticmethod
    def download_file(url: str, **kwargs) -> Optional[BytesIO]:
        kwargs.setdefault('stream', True)
        http = Http.get(url, **kwargs)
        if http.ok:
            f = BytesIO()
            for data in http.iter_content(1024):
                f.write(data)

            return f
