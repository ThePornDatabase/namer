"""
Tests for namer_file_parser.py
"""
import io
from pathlib import Path
from platform import system
import tempfile
import unittest
from unittest.mock import patch

from namer.fileutils import main, set_permissions
from test.utils import sample_config

REGEX_TOKEN = "{_site}{_sep}{_optional_date}{_ts}{_name}{_dot}{_ext}"


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    @patch("sys.stdout", new_callable=io.StringIO)
    @patch("namer.fileutils.default_config")
    def test_main_method(self, config_mock, mock_stdout):
        """
        Test the main method.
        """
        config = sample_config()
        config.min_file_size = 0
        config_mock.side_effect = [config]
        filename: str = 'EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4'
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            target = (tempdir / filename)
            with open(target, 'w'):
                pass
            main(arg_list=["-f", str(target)])
            self.assertIn("site: EvilAngel", mock_stdout.getvalue())

    def test_set_permission(self):
        """
        Verify set permission.
        """
        if system() != "Windows":
            with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
                tempdir = Path(tmpdir)
                target_dir = tempdir / "target_dir"
                target_dir.mkdir()
                testfile = target_dir / "test_file.txt"
                with open(testfile, "w", encoding="utf-8") as file:
                    file.write("Create a new text file!")
                self.assertEqual(oct(testfile.stat().st_mode)[-3:], "644")
                self.assertEqual(oct(target_dir.stat().st_mode)[-3:], "755")
                self.assertNotEqual(target_dir.stat().st_gid, "1234567890")
                config = sample_config()
                config.set_dir_permissions = 777
                config.set_file_permissions = 666
                set_permissions(testfile, config)
                self.assertEqual(oct(testfile.stat().st_mode)[-3:], "666")
                set_permissions(target_dir, config)
                self.assertEqual(oct(target_dir.stat().st_mode)[-3:], "777")


if __name__ == "__main__":
    unittest.main()
