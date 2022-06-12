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
    def get(url, params=None, **kwargs):
        return requests.get(url, params=params, **kwargs)
