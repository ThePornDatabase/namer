import contextlib
import os
import unittest
import warnings
from platform import system
from sys import gettrace as sys_gettrace

import requests
from selenium.webdriver import Chrome, ChromeOptions, Edge, EdgeOptions, Safari
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.safari.service import Service as SafariService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from namer.configuration import NamerConfig
from namer.configuration_utils import default_config
from namer.watchdog import create_watcher
from test.namer_metadataapi_test import environment
from test.namer_watchdog_test import make_locations, new_ea
from test.web.namer_web_pageobjects import FailedPage
from test.web.parrot_webserver import ParrotWebServer


def is_debugging():
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
    if (system() == 'Linux' and os.environ.get("DISPLAY") is None) or not debug:
        options.headless = True
    if system() != 'Windows' and os.geteuid() == 0:
        options.add_argument("--no-sandbox")
    service = EdgeService(executable_path=EdgeChromiumDriverManager().install(), log_path=os.devnull)  # type: ignore
    webdriver = Edge(service=service, options=options)
    return webdriver


def safari_factory(debug: bool) -> WebDriver:
    service = SafariService()
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        return Safari(service=service)


def default_os_browser(debug: bool) -> WebDriver:
    name = system()
    if name == 'Windows':
        return edge_factory(debug)
    # until github actions
    # if name in ['Darwin', 'macOS']:
    #    return safari_factory(debug)
    return chrome_factory(debug)


@contextlib.contextmanager  # type: ignore
def make_test_context(config: NamerConfig):
    with environment(config) as (tempdir, mock_tpdb, config):
        new_config = make_locations(tempdir)
        config.watch_dir = new_config.watch_dir
        config.dest_dir = new_config.dest_dir
        config.failed_dir = new_config.failed_dir
        config.work_dir = new_config.work_dir
        with create_watcher(config) as watcher:
            url = f"http://{config.host}:{watcher.get_web_port()}{config.web_root}/failed"
            with default_os_browser(is_debugging()) as browser:
                browser.get(url)
                yield tempdir, watcher, browser, mock_tpdb


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    def test_webdriver_flow(self: unittest.TestCase):
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
        with make_test_context(config) as (_tempdir, _watcher, browser, _mock_tpdb):
            new_ea(config.failed_dir, use_dir=False)
            (FailedPage(browser).refresh_items()
                .navigate_to().queue_page()
                .navigate_to().failed_page()
                .items()[0]
                .file_name().is_equal_to("EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!").on_success()
                .file_extension().is_equal_to("MP4").on_success()
                .show_log_modal().log_text().is_empty().on_success().close()
                .items()[0]
                .show_search_modal()
                .search()
                .results()[0].title_text().is_equal_to('Carmela Clutch: Fabulous Anal 3-Way!').on_success()
                .date_text().is_equal_to('2022-01-03').on_success()
                .select()  # returns to failed page
                .assert_has_no_files())
        print("done")

    def test_parrot(self):
        with ParrotWebServer() as parrot:
            parrot.set_response("/test?", bytearray("response", 'utf-8'))
            url = parrot.get_url()

            headers = {
                "Authorization": "Bearer token",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "namer-1",
            }
            # while True:
            #    time.sleep(.2)
            with requests.request("GET", f"{url}test", headers=headers) as response:
                response.raise_for_status()
                self.assertEqual(response.text, "response")
