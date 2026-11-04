import http.cookiejar
from enum import Enum
from io import BytesIO
from typing import Optional

import requests
import requests.adapters
import requests.cookies
import requests.models
from loguru import logger
from requests_cache import CachedSession


def patch_requests_type_annotations():
    """
    Workaround for requests 2.34.0+ runtime bug (psf/requests#7456) where types referenced
    in class annotations (RequestsCookieJar, HTTPAdapter, CookieJar, Self) were only imported
    under TYPE_CHECKING in requests.models, causing typing.get_type_hints() and cattrs/attrs
    serialization in requests-cache to fail with NameError.
    """
    try:
        from typing import Self
    except ImportError:
        from typing_extensions import Self

    for name, target in (
        ('RequestsCookieJar', requests.cookies.RequestsCookieJar),
        ('HTTPAdapter', requests.adapters.HTTPAdapter),
        ('CookieJar', http.cookiejar.CookieJar),
        ('Self', Self),
    ):
        if not hasattr(requests.models, name):
            setattr(requests.models, name, target)


patch_requests_type_annotations()


class RequestType(Enum):
    GET = 'GET'
    POST = 'POST'
    HEAD = 'HEAD'


class Http:
    @staticmethod
    def request(method: RequestType, url, **kwargs):
        logger.debug(f'Requesting {method.value} "{url}"')
        cache_session: Optional[CachedSession] = kwargs.get('cache_session')
        if 'cache_session' in kwargs:
            del kwargs['cache_session']

        if kwargs.get('stream', False) or not isinstance(cache_session, CachedSession):
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

        return None
