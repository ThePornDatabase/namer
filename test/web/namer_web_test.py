import contextlib
import os
import tempfile
import unittest
import requests
from pathlib import Path
from platform import system
from sys import gettrace as sys_gettrace
from unittest.mock import MagicMock, patch


from selenium.webdriver import Chrome, ChromeOptions, Edge, EdgeOptions, Safari
from selenium.webdriver.safari.options import Options as SafariOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService

from selenium.webdriver.remote.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from namer.watchdog import create_watcher
from test.namer_watchdog_test import make_locations, new_ea, prepare
from test.web.namer_web_pageobjects import FailedPage
from namer.types import NamerConfig, default_config
from test.web.parrot_webserver import ParrotWebserver


def isdebugging():
    return sys_gettrace() is not None


def chrome_factory(debug: bool) -> WebDriver:
    options = ChromeOptions()
    if (system() == 'Linux' and os.environ.get("DISPLAY") is None) or not debug:
        options.headless = True
    if system() != 'Windows' and os.geteuid() == 0:
        options.add_argument("--no-sandbox")
    service = ChromeService(executable_path=ChromeDriverManager().install(), log_path=os.devnull)  # type: ignore
    return Chrome(service=service, options=options)


def edge_factory(debug: bool) -> WebDriver:
    options = EdgeOptions()
    service = EdgeService(executable_path=EdgeChromiumDriverManager().install(), log_path=os.devnull)  # type: ignore
    webdriver = Edge(service=service, options=options)
    return webdriver


def safari_factory(debug: bool) -> WebDriver:
    options = SafariOptions()
    return Safari(options=options)


def default_os_browser(debug: bool) -> WebDriver:
    if (system() == 'Windows'):
        return edge_factory(debug)
    if (system() == 'macOS'):
        return safari_factory(debug)
    return chrome_factory(debug)


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
            with default_os_browser(isdebugging()) as browser:
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
        with make_test_context(config) as (_tempdir, _watcher, browser):
            targets = [new_ea(config.failed_dir, use_dir=False)]
            prepare(targets, mock_poster, mock_response)
            (FailedPage(browser).refresh_items()
                .navigate_to().queue_page()
                .navigate_to().failed_page()
                .items()[0]
                .file_name().is_equal_to("EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!").on_success()
                .file_extension().is_equal_to("MP4").on_success()
                .show_log_modal().log_text().is_empty())
        print("done")

    def test_parrot(self):
        parrot = ParrotWebserver()
        with ParrotWebserver() as parrot:
            parrot.set_response("test", bytearray("response", 'utf-8'))
            url = parrot.get_url()

            headers = {
                "Authorization": "Bearer token",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "namer-1",
            }
            # while True:
            #    time.sleep(.2)
            with requests.request("GET", f"{url}/test", headers=headers) as response:
                response.raise_for_status()
                self.assertEqual(response.text, "response")
