"""
Tests namer_configparser
"""

from configupdater import ConfigUpdater
import unittest
from importlib import resources

from loguru import logger

from namer.configuration import NamerConfig
from namer.configuration_utils import from_config, to_ini
from test import utils


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    def __init__(self, method_name='runTest'):
        super().__init__(method_name)

        if not utils.is_debugging():
            logger.remove()

    def test_configuration(self) -> None:
        updater = ConfigUpdater(allow_no_value=True)
        config_str = ''
        if hasattr(resources, 'files'):
            config_str = resources.files('namer').joinpath('namer.cfg.default').read_text()
        elif hasattr(resources, 'read_text'):
            config_str = resources.read_text('namer', 'namer.cfg.default')
        updater.read_string(config_str)
        namer_config = from_config(updater, NamerConfig())
        namer_config.config_updater = updater
        namer_config.sites_with_no_date_info = ['badsite']
        ini_content = to_ini(namer_config)
        self.assertIn('sites_with_no_date_info = badsite', ini_content.splitlines())

        updated = ConfigUpdater(allow_no_value=True)
        lines = ini_content.splitlines()
        lines.remove('sites_with_no_date_info = badsite')
        files_no_sites_with_no_date_info = '\n'.join(lines)

        updated.read_string(files_no_sites_with_no_date_info)
        double_read = NamerConfig()
        double_read = from_config(updated, double_read)
        self.assertEqual(double_read.sites_with_no_date_info, [])
        updated.read_string(ini_content)
        double_read = from_config(updated, double_read)
        self.assertIn('badsite', double_read.sites_with_no_date_info)

        updated.read_string(files_no_sites_with_no_date_info)
        double_read = from_config(updated, double_read)
        self.assertIn('badsite', double_read.sites_with_no_date_info)
