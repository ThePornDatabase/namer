"""
Fully test namer.py
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test.utils import new_ea, prepare, sample_config, validate_mp4_tags

from mutagen.mp4 import MP4

from namer.namer import check_arguments, determine_target_file, find_target_file, main, set_permissions
from namer.types import NamerConfig


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    def test_target_file_determination(self):
        """
        Verify artificial names for directories are built correctly.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            config = sample_config()
            config.watch_dir = tempdir
            dir_to_process = (tempdir / "BrazzersExxtra - 2021-12-07 - Dr. Polla & the Chronic Discharge Conundrum")
            new_ea(dir_to_process, use_dir=True)
            results = determine_target_file(dir_to_process, config)
            self.assertIsNotNone(results.parsed_file)
            if results.parsed_file is not None:
                self.assertEqual(results.parsed_file.name, "Dr  Polla & the Chronic Discharge Conundrum")

    def test_check_arguments(self):
        """
        verify file system checks
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            target_dir = tempdir / "path/"
            file = tempdir / "file"
            config = tempdir / "config"
            error = check_arguments(dir_to_process=target_dir, file_to_process=file, config_override=config)
            self.assertTrue(error)
            target_dir.mkdir()
            file.write_text("test")
            config.write_text("test")
            error = check_arguments(dir_to_process=target_dir, file_to_process=file, config_override=config)
            self.assertFalse(error)

    @patch("namer.metadataapi.__get_response_json_object")
    @patch("namer.namer.get_image")
    def test_writing_metadata_file(self, mock_poster, mock_response):
        """
        test namer main method renames and tags in place when -f (video file) is passed
        """
        os.environ["NAMER_CONFIG"] = "./namer.cfg.sample"
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            targets = [new_ea(tempdir, use_dir=False)]
            prepare(targets, mock_poster, mock_response)
            main(["-f", str(targets[0].file)])
            output = MP4(targets[0].file.parent / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4")
            self.assertEqual(output.get("\xa9nam"), ["Carmela Clutch: Fabulous Anal 3-Way!"])

    @patch("namer.metadataapi.__get_response_json_object")
    @patch("namer.namer.get_image")
    def test_writing_metadata_dir(self, mock_poster, mock_response):
        """
        test namer main method renames and tags in place when -d (directory) is passed
        """
        os.environ["NAMER_CONFIG"] = "./namer.cfg.sample"
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            targets = [new_ea(tempdir, use_dir=True)]
            prepare(targets, mock_poster, mock_response)
            main(["-d", str(targets[0].file.parent)])
            output = MP4(targets[0].file.parent / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4")
            self.assertEqual(output.get("\xa9nam"), ["Carmela Clutch: Fabulous Anal 3-Way!"])

    @patch("namer.metadataapi.__get_response_json_object")
    @patch("namer.namer.get_image")
    def test_writing_metadata_all_dirs(self, mock_poster, mock_response):
        """
        Test multiple directories are processed when -d (directory) and -m are passed.
        Process all subdirs of -d.
        """
        os.environ["NAMER_CONFIG"] = "./namer.cfg.sample"
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            targets = [new_ea(tempdir, use_dir=True, post_stem="1"), new_ea(tempdir, use_dir=True, post_stem="2"), ]
            prepare(targets, mock_poster, mock_response)
            main(["-d", str(targets[0].file.parent.parent), "-m"])
            output = MP4(targets[0].file.parent / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4")
            self.assertEqual(output.get("\xa9nam"), ["Carmela Clutch: Fabulous Anal 3-Way!"])
            output = MP4(targets[1].file.parent / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4")
            self.assertEqual(output.get("\xa9nam"), ["Carmela Clutch: Fabulous Anal 3-Way!"])

    def test_writing_metadata_from_nfo(self):
        """
        Test renaming and writing a movie's metadata from a nfo file.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            current = Path(__file__).resolve().parent
            tempdir = Path(tmpdir)
            nfo_file = current / "ea.nfo"
            mp4_file = current / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4"
            poster_file = current / "poster.png"
            target_nfo_file = tempdir / "ea.nfo"
            target_mp4_file = tempdir / "ea.mp4"
            target_poster_file = tempdir / "poster.png"
            shutil.copy(mp4_file, target_mp4_file)
            shutil.copy(nfo_file, target_nfo_file)
            shutil.copy(poster_file, target_poster_file)

            main(["-f", str(target_mp4_file), "-i"])
            output = MP4(target_mp4_file.parent / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4")
            self.assertEqual(output.get("\xa9nam"), ["Carmela Clutch: Fabulous Anal 3-Way!"])

    @patch("namer.metadataapi.__get_response_json_object")
    @patch("namer.namer.get_image")
    def test_writing_metadata_all_dirs_files(self, mock_poster, mock_response):
        """
        Test multiple directories are processed when -d (directory) and -m are passed.
        Process all sub-dirs of -d.
        """
        os.environ["NAMER_CONFIG"] = "./namer.cfg.sample"
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            targets = [new_ea(tempdir, use_dir=False, post_stem="1"), new_ea(tempdir, use_dir=False, post_stem="2")]
            prepare(targets, mock_poster, mock_response)
            main(["-d", str(targets[0].file.parent), "-m"])
            output1 = (targets[0].file.parent / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4")
            validate_mp4_tags(self, output1)
            output2 = (targets[1].file.parent / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!(1).mp4")
            validate_mp4_tags(self, output2)

    def test_find_target_file(self):
        """
        Test set permissions
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            path = Path(tmpdir)
            test_file = path / "test_file.avi"
            test_file.write_text("test")
            config = sample_config()
            target = find_target_file(path, config)
            self.assertEqual(target, test_file)

    def test_set_permissions(self):
        """
        Test set permissions
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            path = Path(tmpdir)
            test_file = path / "test_file.txt"
            test_file.write_text("test")
            test_dir = path / "test_dir"
            test_dir.mkdir()
            config = NamerConfig()
            if hasattr(os, "getgroups"):
                config.set_gid = None if len(os.getgroups()) == 0 else os.getgroups()[0]
            if hasattr(os, "getuid"):
                config.set_uid = os.getuid()
            config.set_dir_permissions = 777
            config.set_file_permissions = 666
            set_permissions(test_file, config)
            self.assertTrue(os.access(test_file, os.R_OK))
            config.set_file_permissions = None
            set_permissions(test_file, config)
            self.assertTrue(os.access(test_file, os.R_OK))
            set_permissions(test_dir, config)
            self.assertTrue(os.access(test_dir, os.R_OK))
            set_permissions(None, config)


if __name__ == "__main__":
    unittest.main()
