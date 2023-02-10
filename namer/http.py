from enum import Enum
from io import BytesIO
from typing import Optional

import requests
from loguru import logger
from requests_cache import CachedSession


class RequestType(Enum):
    GET = 'GET'
    POST = 'POST'
    HEAD = 'HEAD'


class Http:  # noqa: PIE798
    @staticmethod
    def request(method: RequestType, url, **kwargs):
        logger.info(f'Requesting {method.value} "{url}"')
        cache_session: Optional[CachedSession] = kwargs.get('cache_session')
        if 'cache_session' in kwargs:
            del kwargs['cache_session']

        if kwargs.get("stream", False) or not isinstance(cache_session, CachedSession):
            return requests.request(method.value, url, **kwargs)
        else:
            return cache_session.request(method.value, url, **kwargs)

    @staticmethod
    def get(url: str, **kwargs):
        return Http.request(RequestType.GET, url, **kwargs)

    @staticmethod
    def post(url: str, **kwargs):
        return Http.request(RequestType.POST, url, **kwargs)

    @staticmethod
    def head(url: str, **kwargs):
        return Http.request(RequestType.HEAD, url, **kwargs)

    @staticmethod
    def download_file(url: str, **kwargs) -> Optional[BytesIO]:
        kwargs.setdefault('stream', True)
        http = Http.get(url, **kwargs)
        if http.ok:
            f = BytesIO()
            for data in http.iter_content(1024):
                f.write(data)

            return f
