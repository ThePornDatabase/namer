"""
Test namer_types.py
"""

import os
import sys
import unittest
from pathlib import Path

from loguru import logger

from namer.configuration import NamerConfig
from namer.configuration_utils import verify_configuration
from namer.name_formatter import PartialFormatter
from namer.comparison_results import Performer
from test import utils


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    def __init__(self, method_name='runTest'):
        super().__init__(method_name)

        if not utils.is_debugging():
            logger.remove()

    def test_performer(self):
        """
        Test performer __str__
        """
        self.assertEqual(str(Performer(None, None)), 'Unknown')
        self.assertEqual(str(Performer('Name', None)), 'Name')
        self.assertEqual(str(Performer(None, 'Role')), 'Unknown (Role)')
        self.assertEqual(str(Performer('Name', 'Role')), 'Name (Role)')

    def test_default_no_config(self):
        """
        verify the default values of NamerConfig
        """
        config = NamerConfig()
        self.assertEqual(config.del_other_files, False)
        self.assertEqual(config.inplace_name, '{full_site} - {date} - {name} [WEBDL-{resolution}].{ext}')
        self.assertEqual(config.enabled_tagging, False)
        self.assertEqual(config.write_namer_log, False)
        self.assertEqual(config.enable_metadataapi_genres, False)
        self.assertEqual(config.default_genre, 'Adult')
        self.assertFalse(hasattr(config, 'dest_dir'))
        self.assertFalse(hasattr(config, 'failed_dir'))
        self.assertEqual(config.min_file_size, 300)
        self.assertEqual(config.language, None)
        if sys.platform != 'win32':
            self.assertEqual(config.set_uid, os.getuid())
            self.assertEqual(config.set_gid, os.getgid())
            self.assertEqual(config.set_dir_permissions, 775)
            self.assertEqual(config.set_file_permissions, 664)

    def test_formatter(self):
        """
        Verify that partial formatter can handle missing fields gracefully,
        and it's prefix, postfix, and infix capabilities work.
        """
        bad_fmt = '---'
        fmt = PartialFormatter(missing='', bad_fmt=bad_fmt)
        name = fmt.format('{name}{act: 1p}', name='scene1', act='act1')
        self.assertEqual(name, 'scene1 act1')
        name = fmt.format('{name}{act: 1p}', name='scene1', act=None)
        self.assertEqual(name, 'scene1')

        name = fmt.format('{name}{act: 1s}', name='scene1', act='act1')
        self.assertEqual(name, 'scene1act1 ')
        name = fmt.format('{name}{act: 1s}', name='scene1', act=None)
        self.assertEqual(name, 'scene1')

        name = fmt.format('{name}{act: 1i}', name='scene1', act='act1')
        self.assertEqual(name, 'scene1 act1 ')
        name = fmt.format('{name}{act: 1i}', name='scene1', act=None)
        self.assertEqual(name, 'scene1')

        name = fmt.format('{name}{act:_1i}', name='scene1', act='act1')
        self.assertEqual(name, 'scene1_act1_')

        name = fmt.format('{name}{act: >10}', name='scene1', act='act1')
        self.assertEqual(name, 'scene1      act1')

        name = fmt.format('{name:|title}{act:|upper}', name='scene1', act='act1')
        self.assertEqual(name, 'Scene1ACT1')

        with self.assertRaises(Exception) as error1:
            name = fmt.format('{name1}{act: >10}', name='scene1', act='act1')
            self.assertEqual(name, 'scene1      act1')
        self.assertTrue('name1' in str(error1.exception))
        self.assertTrue('all_performers' in str(error1.exception))

        self.assertEqual(fmt.format_field(format_spec='adsfadsf', value='fmt'), bad_fmt)

        with self.assertRaises(Exception) as error2:
            fmt1 = PartialFormatter(missing='', bad_fmt=None)  # type: ignore
            fmt1.format_field(format_spec='adsfadsf', value='fmt')
        self.assertTrue('Invalid format specifier' in str(error2.exception))

    def test_config_verification(self):
        """
        Verify config verification.
        """
        config = NamerConfig()
        success = verify_configuration(config, PartialFormatter())
        self.assertEqual(success, True)

        config = NamerConfig()
        config.watch_dir = Path('/not/a/real/path')
        success = verify_configuration(config, PartialFormatter())
        self.assertEqual(success, False)

        config = NamerConfig()
        config.work_dir = Path('/not/a/real/path')
        success = verify_configuration(config, PartialFormatter())
        self.assertEqual(success, False)

        config = NamerConfig()
        config.failed_dir = Path('/not/a/real/path')
        success = verify_configuration(config, PartialFormatter())
        self.assertEqual(success, False)

        config = NamerConfig()
        config.inplace_name = '{sitesadf} - {date}'
        success = verify_configuration(config, PartialFormatter())
        self.assertEqual(success, False)

        config1 = NamerConfig()
        config1.new_relative_path_name = '{whahha}/{site} - {date}'
        success = verify_configuration(config, PartialFormatter())
        self.assertEqual(success, False)


if __name__ == '__main__':
    unittest.main()
