import os
from pathlib import Path
from platform import system
import tempfile
import unittest
from sys import gettrace as sys_gettrace
from unittest.mock import MagicMock, patch
from selenium.webdriver.chrome.service import Service
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from test.namer_watchdog_test import make_locations, new_ea, prepare
from namer.watchdog import create_watcher


def isdebugging():
    return sys_gettrace() is not None


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    @patch("namer.metadataapi.__get_response_json_object")
    @patch("namer.namer.get_image")
    @patch("namer.namer.default_config")
    def test_webdriver_flow(self: unittest.TestCase, mock_config: MagicMock, mock_poster: MagicMock, mock_response: MagicMock):
        """
        Test we can start the app, install, run and control a browser and shut it all down safely.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            config = make_locations(tempdir)
            config.web = True
            config.web_root = "/namer"
            config.host = '127.0.0.1'
            config.port = 0
            config.allow_delete_files = True
            config.write_nfo = False
            config.min_file_size = 0
            mock_config.return_value = config
            targets = [new_ea(config.failed_dir, use_dir=False)]
            prepare(targets, mock_poster, mock_response)
            with create_watcher(config) as watcher:
                url = f"http://{config.host}:{watcher.get_web_port()}{config.web_root}"
                options = ChromeOptions()
                if (system() == 'Linux' and os.environ.get("DISPLAY") is None) or not isdebugging():
                    options.headless = True
                if system() != 'Windows' and os.geteuid() == 0:
                    options.add_argument("--no-sandbox")
                service = Service(ChromeDriverManager().install(), log_path=os.devnull)
                with Chrome(service=service, options=options) as browser:
                    browser.get(url)
                    element = browser.find_element(by=By.ID, value="refreshFiles")
                    element.click()
        print("done")