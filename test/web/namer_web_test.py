import contextlib
import os
import tempfile
import unittest
from pathlib import Path
from platform import system
from sys import gettrace as sys_gettrace
from unittest.mock import MagicMock, patch

from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from namer.watchdog import create_watcher
from test.namer_watchdog_test import make_locations, new_ea, prepare
from test.web.namer_web_pageobjects import FailedPage
from namer.types import NamerConfig, default_config

_browser = Chrome
_options = ChromeOptions
_manager = ChromeDriverManager


def isdebugging():
    return sys_gettrace() is not None


@contextlib.contextmanager
def make_test_context(config: NamerConfig):
    with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
        tempdir = Path(tmpdir)
        new_config = make_locations(tempdir)
        config.watch_dir = new_config.watch_dir
        config.dest_dir = new_config.dest_dir
        config.failed_dir = new_config.failed_dir
        config.work_dir = new_config.work_dir
        with create_watcher(config) as watcher:
            url = f"http://{config.host}:{watcher.get_web_port()}{config.web_root}/failed"
            options = _options()
            if (system() == 'Linux' and os.environ.get("DISPLAY") is None) or not isdebugging():
                options.headless = True
            if system() != 'Windows' and os.geteuid() == 0:
                options.add_argument("--no-sandbox")
            service = Service(_manager().install(), log_path=os.devnull)
            with _browser(service=service, options=options) as browser:
                browser.get(url)
                yield (tempdir, watcher, browser)


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    @patch("namer.metadataapi.__get_response_json_object")
    @patch("namer.namer.get_image")
    def test_webdriver_flow(self: unittest.TestCase, mock_poster: MagicMock, mock_response: MagicMock):
        """
        Test we can start the app, install, run and control a browser and shut it all down safely.
        """
        config = default_config()
        config.web = True
        config.web_root = "/namer"
        config.host = '127.0.0.1'
        config.port = 0
        config.allow_delete_files = True
        config.write_nfo = False
        config.min_file_size = 0
        with make_test_context(config) as (__tempdir, __watcher, browser):
            targets = [new_ea(config.failed_dir, use_dir=False)]
            prepare(targets, mock_poster, mock_response)
            (FailedPage(browser).refresh_items()
                .navigate_to().queue_page()
                .navigate_to().failed_page()
                .items()[0]
                .file_name().is_equal_to("EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!").on_success()
                .file_extension().is_equal_to("MP4").does_not_contain("XYZ").on_success()
                .show_log_modal().log_text().is_empty())
        print("done")
