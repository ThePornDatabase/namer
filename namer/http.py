import tempfile
from datetime import timedelta
from pathlib import Path

import requests
import requests_cache

from namer.types import NamerConfig


class Http:
    def __init__(self, namer_config: NamerConfig):
        if namer_config.enabled_requests_cache:
            cache_file = Path(tempfile.gettempdir()) / "namer_cache"
            expire_time = timedelta(minutes=namer_config.requests_cache_expire_minutes)
            requests_cache.install_cache(str(cache_file), expire_after=expire_time, ignored_parameters=["Authorization"])

    @staticmethod
    def request(method, url, **kwargs):
        if kwargs.get("stream", False):
            with requests_cache.disabled():
                return requests.request(method, url, **kwargs)
        else:
            return requests.request(method, url, **kwargs)

    @staticmethod
    def get(url: str, **kwargs):
        return Http.request("GET", url, **kwargs)

    @staticmethod
    def post(url: str, **kwargs):
        return Http.request("POST", url, **kwargs)

    @staticmethod
    def head(url: str, **kwargs):
        return Http.request("HEAD", url, **kwargs)
