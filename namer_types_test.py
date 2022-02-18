"""
Test namer_types.py
"""
from configparser import ConfigParser
import logging
import os
from pathlib import Path
import sys
import unittest
from namer_types import NamerConfig, default_config, PartialFormatter, from_config


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    current=os.path.dirname(os.path.abspath(__file__))

    def test_local_config(self):
        """
        Verify the namer.cfg exmple in this directory is loaded.
        """
        config = default_config()
        self.assertEqual(config.del_other_files , False)
        self.assertEqual(config.inplace_name, '{site} - {date} - {name}.{ext}')
        self.assertEqual(config.new_relative_path_name, '{site} - {date} - {name}/{site} - {date} - {name}.{ext}')
        self.assertEqual(config.dest_dir.parts, ('test','dest'))
        self.assertEqual(config.failed_dir.parts , ('test','failed'))
        self.assertEqual(config.min_file_size, 300)
        self.assertEqual(config.language, 'eng')

    def test_default_no_config(self):
        """
        verify the default values of NamerConfig
        """
        config = NamerConfig()
        self.assertEqual(config.del_other_files , False)
        self.assertEqual(config.inplace_name, '{site} - {date} - {name}.{ext}')
        self.assertEqual(config.enabled_tagging, True)
        self.assertEqual(config.write_namer_log, False)
        self.assertEqual(config.enable_metadataapi_genres, False)
        self.assertEqual(config.default_genre, 'Adult')
        self.assertEqual(config.dest_dir, None)
        self.assertEqual(config.failed_dir, None)
        self.assertEqual(config.min_file_size, 300)
        self.assertEqual(config.language, None)
        if sys.platform != "win32":
            self.assertEqual(config.set_uid, os.getuid())
            self.assertEqual(config.set_gid, os.getgid())
            self.assertEqual(config.set_dir_permissions, 775)
            self.assertEqual(config.set_file_permissions, 664)

    def test_formatter(self):
        """
        Verify that partial formatter can handle missing fields gracefully,
        and it's prefix, postfix, and infix capabilities work.
        """
        fmt = PartialFormatter(missing='',bad_fmt='---')
        name = fmt.format("{name}{act: 1p}", name='scene1', act='act1')
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

        with self.assertRaises(Exception) as context:
            name = fmt.format('{name1}{act: >10}', name='scene1', act='act1')
            self.assertEqual(name, 'scene1      act1')
        self.assertTrue('name1' in str(context.exception))
        self.assertTrue('all_performers' in str(context.exception) )

    def test_config_verification(self):
        """
        Verify config verification.
        """
        logging.basicConfig(level=logging.INFO)
        config = NamerConfig()
        success = config.verify_config()
        self.assertEqual(success, True)

        config = NamerConfig()
        config.watch_dir=Path("/not/a/real/path")
        success = config.verify_config()
        self.assertEqual(success, False)

        config = NamerConfig()
        config.work_dir=Path("/not/a/real/path")
        success = config.verify_config()
        self.assertEqual(success, False)

        config = NamerConfig()
        config.failed_dir=Path("/not/a/real/path")
        success = config.verify_config()
        self.assertEqual(success, False)

        config = NamerConfig()
        config.inplace_name="{sitesadf} - {date}"
        success = config.verify_config()
        self.assertEqual(success, False)

        config1 = NamerConfig()
        config1.new_relative_path_name='{whahha}/{site} - {date}'
        success = config1.verify_config()
        self.assertEqual(success, False)

    def test_from_config(self):
        """
        Verify config reader does it's job.
        """
        config = ConfigParser()
        non_default_all_config = """
        [namer]
            porndb_token = mytoken
            inplace_name={site} - {name}.{ext}
            prefer_dir_name_if_available = False
            min_file_size = 69
            write_namer_log = True
            set_dir_permissions = 700
            set_file_permissions = 700

        [metadata]
            enabled_tagging = False
            enabled_poster = False
            enable_metadataapi_genres = True
            default_genre = Pron
            language = rus

        [watchdog]
            del_other_files = True
            new_relative_path_name={site} - {name}/{site} - {name}.{ext}
            watch_dir = /notarealplace/watch
            work_dir = /notarealplace/work
            failed_dir = /notarealplace/failed
            dest_dir = /notarealplace/dest
            retry_time = 02:16
        """
        config.read_string(non_default_all_config)
        namer_config = from_config(config)
        self.assertEqual(namer_config.porndb_token, "mytoken")
        self.assertEqual(namer_config.inplace_name, "{site} - {name}.{ext}")
        self.assertEqual(namer_config.prefer_dir_name_if_available, False)
        self.assertEqual(namer_config.min_file_size, 69)
        self.assertEqual(namer_config.write_namer_log, True)
        self.assertEqual(namer_config.set_dir_permissions, "700")
        self.assertEqual(namer_config.set_file_permissions, "700")
        self.assertEqual(namer_config.enabled_tagging, False)
        self.assertEqual(namer_config.enabled_poster, False)
        self.assertEqual(namer_config.enable_metadataapi_genres, True)
        self.assertEqual(namer_config.default_genre, "Pron")
        self.assertEqual(namer_config.language, "rus")
        self.assertEqual(namer_config.del_other_files, True)
        self.assertEqual(namer_config.new_relative_path_name, "{site} - {name}/{site} - {name}.{ext}")
        self.assertEqual(str(namer_config.watch_dir), "/notarealplace/watch")
        self.assertEqual(str(namer_config.work_dir), "/notarealplace/work")
        self.assertEqual(str(namer_config.dest_dir), "/notarealplace/dest")
        self.assertEqual(str(namer_config.failed_dir), "/notarealplace/failed")
        self.assertEqual(namer_config.retry_time, "02:16")

if __name__ == '__main__':
    unittest.main()
