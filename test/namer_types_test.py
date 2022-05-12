"""
Test namer_types.py
"""
from configparser import ConfigParser
import logging
import os
from pathlib import Path
from platform import system
import sys
import tempfile
import unittest
from test.utils import sample_config
from namer.types import (
    NamerConfig,
    PartialFormatter,
    Performer,
    from_config,
    set_permissions,
)


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    def test_performer(self):
        """
        Test performer __str__
        """
        self.assertEqual(str(Performer(None, None)), "Unknown")
        self.assertEqual(str(Performer("Name", None)), "Name")
        self.assertEqual(str(Performer(None, "Role")), "Unknown (Role)")
        self.assertEqual(str(Performer("Name", "Role")), "Name (Role)")

    def test_local_config(self):
        """
        Verify the namer.cfg exmple in this directory is loaded.
        """
        config = sample_config()
        self.assertEqual(config.del_other_files, False)
        self.assertEqual(config.inplace_name, "{site} - {date} - {name}.{ext}")
        self.assertEqual(
            config.new_relative_path_name,
            "{site} - {date} - {name}/{site} - {date} - {name}.{ext}",
        )
        self.assertEqual(config.dest_dir.parts, ("test", "dest"))
        self.assertEqual(config.failed_dir.parts, ("test", "failed"))
        self.assertEqual(config.min_file_size, 300)
        self.assertEqual(config.language, "eng")

    def test_default_no_config(self):
        """
        verify the default values of NamerConfig
        """
        config = NamerConfig()
        self.assertEqual(config.del_other_files, False)
        self.assertEqual(config.inplace_name, "{site} - {date} - {name}.{ext}")
        self.assertEqual(config.enabled_tagging, True)
        self.assertEqual(config.write_namer_log, False)
        self.assertEqual(config.enable_metadataapi_genres, False)
        self.assertEqual(config.default_genre, "Adult")
        self.assertFalse(hasattr(config, "dest_dir"))
        self.assertFalse(hasattr(config, "failed_dir"))
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
        badfmt = "---"
        fmt = PartialFormatter(missing="", bad_fmt=badfmt)
        name = fmt.format("{name}{act: 1p}", name="scene1", act="act1")
        self.assertEqual(name, "scene1 act1")
        name = fmt.format("{name}{act: 1p}", name="scene1", act=None)
        self.assertEqual(name, "scene1")

        name = fmt.format("{name}{act: 1s}", name="scene1", act="act1")
        self.assertEqual(name, "scene1act1 ")
        name = fmt.format("{name}{act: 1s}", name="scene1", act=None)
        self.assertEqual(name, "scene1")

        name = fmt.format("{name}{act: 1i}", name="scene1", act="act1")
        self.assertEqual(name, "scene1 act1 ")
        name = fmt.format("{name}{act: 1i}", name="scene1", act=None)
        self.assertEqual(name, "scene1")

        name = fmt.format("{name}{act:_1i}", name="scene1", act="act1")
        self.assertEqual(name, "scene1_act1_")

        name = fmt.format("{name}{act: >10}", name="scene1", act="act1")
        self.assertEqual(name, "scene1      act1")

        with self.assertRaises(Exception) as error1:
            name = fmt.format("{name1}{act: >10}", name="scene1", act="act1")
            self.assertEqual(name, "scene1      act1")
        self.assertTrue("name1" in str(error1.exception))
        self.assertTrue("all_performers" in str(error1.exception))

        self.assertEqual(fmt.format_field(
            format_spec="adsfadsf", value="fmt"), badfmt)

        with self.assertRaises(Exception) as error2:
            fmt1 = PartialFormatter(missing="", bad_fmt=None)
            fmt1.format_field(format_spec="adsfadsf", value="fmt")
        self.assertTrue("Invalid format specifier" in str(error2.exception))

    def test_config_verification(self):
        """
        Verify config verification.
        """
        logging.basicConfig(level=logging.INFO)
        config = NamerConfig()
        success = config.verify_watchdog_config()
        self.assertEqual(success, True)

        config = NamerConfig()
        config.watch_dir = Path("/not/a/real/path")
        success = config.verify_watchdog_config()
        self.assertEqual(success, False)

        config = NamerConfig()
        config.work_dir = Path("/not/a/real/path")
        success = config.verify_watchdog_config()
        self.assertEqual(success, False)

        config = NamerConfig()
        config.failed_dir = Path("/not/a/real/path")
        success = config.verify_watchdog_config()
        self.assertEqual(success, False)

        config = NamerConfig()
        config.inplace_name = "{sitesadf} - {date}"
        success = config.verify_naming_config()
        self.assertEqual(success, False)

        config1 = NamerConfig()
        config1.new_relative_path_name = "{whahha}/{site} - {date}"
        success = config1.verify_watchdog_config()
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
            trailer_location = trailer/default.{ext}
            sites_with_no_date_info = Milf, TeamWhatever

        [metadata]
            write_nfo = True
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
        self.assertEqual(namer_config.set_dir_permissions, 700)
        self.assertEqual(namer_config.set_file_permissions, 700)
        self.assertEqual(namer_config.trailer_location,
                         "trailer/default.{ext}")
        self.assertEqual(namer_config.write_nfo, True)
        self.assertEqual(namer_config.sites_with_no_date_info,
                         ["MILF", "TEAMWHATEVER"])
        self.assertEqual(namer_config.enabled_tagging, False)
        self.assertEqual(namer_config.enabled_poster, False)
        self.assertEqual(namer_config.enable_metadataapi_genres, True)
        self.assertEqual(namer_config.default_genre, "Pron")
        self.assertEqual(namer_config.language, "rus")
        self.assertEqual(namer_config.del_other_files, True)
        self.assertEqual(
            namer_config.new_relative_path_name, "{site} - {name}/{site} - {name}.{ext}"
        )
        self.assertEqual(namer_config.watch_dir, Path("/notarealplace/watch"))
        self.assertEqual(namer_config.work_dir, Path("/notarealplace/work"))
        self.assertEqual(namer_config.dest_dir, Path("/notarealplace/dest"))
        self.assertEqual(namer_config.failed_dir,
                         Path("/notarealplace/failed"))
        self.assertEqual(namer_config.retry_time, "02:16")

    def test_main_method(self):
        """
        Test config to string
        """
        config = sample_config()
        conf = str(config)
        self.assertIn("Namer Config", conf)
        self.assertIn("Watchdog Config", conf)

    def test_set_permission(self):
        """
        Verify set permission.
        """
        if system() != "Windows":
            with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
                tempdir = Path(tmpdir)
                targetdir = tempdir / "targetdir"
                targetdir.mkdir()
                testfile = targetdir / "testfile.txt"
                with open(testfile, "w", encoding="utf-8") as file:
                    file.write("Create a new text file!")
                self.assertEqual(oct(testfile.stat().st_mode)[-3:], "644")
                self.assertEqual(oct(targetdir.stat().st_mode)[-3:], "755")
                self.assertNotEqual(targetdir.stat().st_gid, "1234567890")
                config = sample_config()
                config.set_dir_permissions = 777
                config.set_file_permissions = 666
                set_permissions(testfile, config)
                self.assertEqual(oct(testfile.stat().st_mode)[-3:], "666")
                set_permissions(targetdir, config)
                self.assertEqual(oct(targetdir.stat().st_mode)[-3:], "777")


if __name__ == "__main__":
    unittest.main()
