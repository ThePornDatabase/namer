import tempfile
from datetime import timedelta
from pathlib import Path

import requests
import requests_cache

from namer.types import default_config

config = default_config()
if config.enabled_requests_cache:
    cache_file = Path(tempfile.gettempdir()) / 'namer_cache'
    expire_time = timedelta(minutes=config.requests_cache_expire_minutes)
    requests_cache.install_cache(str(cache_file), expire_after=expire_time)


class Http:
    @staticmethod
    def request(method, url, **kwargs):
        return requests.request(method, url, **kwargs)

    @staticmethod
    def get(url: str, **kwargs):
        return Http.request('GET', url, **kwargs)

    @staticmethod
    def post(url: str, **kwargs):
        return Http.request('POST', url, **kwargs)

    @staticmethod
    def head(url: str, **kwargs):
        return Http.request('HEAD', url, **kwargs)
