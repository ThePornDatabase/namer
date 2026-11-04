import http.cookiejar
import tempfile
import typing
import unittest
from pathlib import Path

import requests.adapters
import requests.cookies
import requests.models
from requests_cache import CachedSession

from namer.http import Http, patch_requests_type_annotations
from test.web.parrot_webserver import ParrotWebServer


class HttpTest(unittest.TestCase):
    def test_requests_models_annotations_patch(self):
        patch_requests_type_annotations()

        self.assertTrue(hasattr(requests.models, 'RequestsCookieJar'))
        self.assertIs(requests.models.RequestsCookieJar, requests.cookies.RequestsCookieJar)
        self.assertTrue(hasattr(requests.models, 'HTTPAdapter'))
        self.assertIs(requests.models.HTTPAdapter, requests.adapters.HTTPAdapter)
        self.assertTrue(hasattr(requests.models, 'CookieJar'))
        self.assertIs(requests.models.CookieJar, http.cookiejar.CookieJar)

        # Ensure typing.get_type_hints resolves Response without NameError
        hints = typing.get_type_hints(requests.models.Response)
        self.assertIn('cookies', hints)

    def test_cached_session_serialization_compatibility(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_path = Path(tmp_dir) / 'test_cache'
            session = CachedSession(str(cache_path), backend='sqlite')
            try:
                with ParrotWebServer() as parrot:
                    parrot.set_response('/test?', bytearray('response', 'utf-8'))
                    url = parrot.get_url()

                    # Make request via Http helper with CachedSession;
                    # triggers requests-cache cattrs serialization into SQLite.
                    res = Http.get(f'{url}/test', cache_session=session)
                    self.assertEqual(res.status_code, 200)
                    self.assertEqual(res.text, 'response')

                    # Retrieve from cache to test cattrs deserialization.
                    res_cached = Http.get(f'{url}/test', cache_session=session)
                    self.assertEqual(res_cached.status_code, 200)
                    self.assertEqual(res_cached.text, 'response')
                    self.assertTrue(res_cached.from_cache)
            finally:
                session.cache.close()


if __name__ == '__main__':
    unittest.main()
