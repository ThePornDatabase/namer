"""
Test namer_watchdog.py
"""
import logging
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from test.utils import new_ea, prepare, sample_config, validate_mp4_tags, validate_permissions

from mutagen.mp4 import MP4

from namer.types import NamerConfig
from namer.watchdog import create_watcher, done_copying, retry_failed


def make_locations(tempdir: Path) -> NamerConfig:
    """
    Make temp testing dirs.
    """
    config = sample_config()
    config.watch_dir = tempdir / "watch"
    config.watch_dir.mkdir()
    config.work_dir = tempdir / "work"
    config.work_dir.mkdir()
    config.dest_dir = tempdir / "dest"
    config.dest_dir.mkdir()
    config.failed_dir = tempdir / "failed"
    config.failed_dir.mkdir()
    config.del_other_files = True
    config.extra_sleep_time = 1
    return config


def wait_until_processed(config: NamerConfig):
    """
    Waits until all files have been moved out of watch/working dirs.
    """
    while len(list(config.watch_dir.iterdir())) > 0 or len(list(config.work_dir.iterdir())) > 0:
        time.sleep(0.2)


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    def test_done_copying_non_existent_file(self):
        """
        Test negatives.
        """
        non_path = Path("should_not_exist")
        self.assertFalse(done_copying(non_path))
        self.assertFalse(done_copying(None))

    @patch("namer.metadataapi.__get_response_json_object")
    @patch("namer.namer.get_image")
    def test_handler_collisions_success(self, mock_poster, mock_response):
        """
        Test the handle function works for a directory.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            config = make_locations(tempdir)
            config.prefer_dir_name_if_available = True
            config.write_namer_log = True
            config.min_file_size = 0
            watcher = create_watcher(config)
            watcher.start()
            targets = [
                new_ea(config.watch_dir),
                new_ea(config.watch_dir, use_dir=False)
            ]
            prepare(targets, mock_poster, mock_response)
            wait_until_processed(config)
            watcher.stop()
            self.assertFalse(targets[0].file.exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            output_file = config.dest_dir / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4"
            output = MP4(output_file)
            self.assertEqual(output.get("\xa9nam"), ["Carmela Clutch: Fabulous Anal 3-Way!"])

            output_file2 = config.dest_dir / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!(1).mp4"
            output2 = MP4(output_file2)
            self.assertEqual(output2.get("\xa9nam"), ["Carmela Clutch: Fabulous Anal 3-Way!"])
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)

    @patch("namer.metadataapi.__get_response_json_object")
    @patch("namer.namer.get_image")
    def test_event_listener_success(self, mock_poster, mock_response):
        """
        Test the handle function works for a directory.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            config = make_locations(tempdir)
            config.prefer_dir_name_if_available = True
            config.min_file_size = 0
            config.write_namer_log = True
            config.min_file_size = 0
            watcher = create_watcher(config)
            watcher.start()
            targets = [new_ea(config.watch_dir)]
            prepare(targets, mock_poster, mock_response)
            wait_until_processed(config)
            watcher.stop()
            self.assertFalse(targets[0].file.exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            output_file = config.dest_dir / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4"
            output = MP4(output_file)
            self.assertEqual(output.get("\xa9nam"), ["Carmela Clutch: Fabulous Anal 3-Way!"])
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)

    @patch("namer.metadataapi.__get_response_json_object")
    @patch("namer.namer.get_image")
    def test_handler_deeply_nested_success_no_dirname(self, mock_poster, mock_response):
        """
        Test the handle function works for a directory.
        """
        os.environ["NAMER_CONFIG"] = "./namer.cfg.sample"
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            os.environ["NAMER_CONFIG"] = "./namer.cfg.sample"
            tempdir = Path(tmpdir)
            config = make_locations(tempdir)
            config.prefer_dir_name_if_available = False
            config.write_namer_log = True
            config.min_file_size = 0
            watcher = create_watcher(config)
            watcher.start()
            targets = [
                new_ea(config.watch_dir / "deeper" / "and_deeper", use_dir=False),
                new_ea(config.watch_dir, post_stem="number2", use_dir=False),
            ]
            prepare(targets, mock_poster, mock_response)
            wait_until_processed(config)
            watcher.stop()
            self.assertFalse(targets[0].file.exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            output_file = config.dest_dir / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4"
            validate_mp4_tags(self, output_file)
            self.assertTrue((output_file.parent / (output_file.stem + "_namer.log")).exists())
            output_file2 = config.dest_dir / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!(1).mp4"
            validate_mp4_tags(self, output_file2)
            validate_permissions(self, output_file2, 664)
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)

    @patch("namer.metadataapi.__get_response_json_object")
    @patch("namer.namer.get_image")
    def test_handler_deeply_nested_success(self, mock_poster, mock_response):
        """
        Test the handle function works for a directory.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            config = make_locations(tempdir)
            config.prefer_dir_name_if_available = True
            config.write_namer_log = True
            config.del_other_files = False
            config.min_file_size = 0
            config.set_dir_permissions = None
            config.set_file_permissions = None
            watcher = create_watcher(config)
            watcher.start()
            targets = [
                new_ea(config.watch_dir / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way", use_dir=True),
            ]
            prepare(targets, mock_poster, mock_response)
            wait_until_processed(config)
            watcher.stop()
            self.assertFalse(targets[0].file.exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            output_file = config.dest_dir / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4"
            validate_mp4_tags(self, output_file)
            validate_permissions(self, output_file, 600)
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)

    def test_handler_ignore(self):
        """
        Test the handle function works for a directory.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            config = make_locations(tempdir)
            config.prefer_dir_name_if_available = False
            config.write_namer_log = True
            config.min_file_size = 0
            watcher = create_watcher(config)
            os.environ.update([
                ("BUILD_DATE", "date"),
                ("GIT_HASH", "hash"),
            ])
            watcher.start()
            targets = [
                new_ea(config.watch_dir / "_UNPACK_stuff" / "EvilAngel - Carmela Clutch Fabulous Anal 3-Way", use_dir=True),
            ]
            time.sleep(2)
            watcher.stop()
            self.assertTrue(targets[0].file.exists())

    @patch("namer.metadataapi.__get_response_json_object")
    @patch("namer.namer.get_image")
    def test_handler_failure(self, mock_poster, mock_response):
        """
        Test the handle function works for a directory.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            config = make_locations(tempdir)
            config.prefer_dir_name_if_available = False
            config.write_namer_log = True
            config.min_file_size = 0
            watcher = create_watcher(config)
            os.environ.update([
                ("BUILD_DATE", "date"),
                ("GIT_HASH", "hash"),
            ])
            watcher.start()
            targets = [new_ea(config.watch_dir, use_dir=False, match=False), ]
            prepare(targets, mock_poster, mock_response)
            wait_until_processed(config)
            watcher.stop()
            self.assertFalse(targets[0].file.exists())
            relative = targets[0].file.relative_to(config.watch_dir)
            work_file = config.work_dir / relative
            self.assertFalse(work_file.exists())
            failed_file = config.failed_dir / relative
            self.assertTrue(failed_file.exists() and failed_file.is_file())
            failed_log_file = failed_file.parent / (failed_file.stem + "_namer.log")
            self.assertTrue(failed_log_file.exists() and failed_log_file.is_file())
            retry_failed(config)
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertGreater(len(list(config.watch_dir.iterdir())), 0)

    @patch("namer.metadataapi.__get_response_json_object")
    @patch("namer.namer.get_image")
    def test_name_parser_success(self, mock_poster, mock_response):
        """
        Test the handle function works for a directory.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            config = make_locations(tempdir)
            config.prefer_dir_name_if_available = True
            config.write_namer_log = True
            config.min_file_size = 0
            config.name_parser = "{_site} - {_ts}{_name}.{_ext}"
            config.sites_with_no_date_info = ["EVILANGEL"]
            watcher = create_watcher(config)
            os.environ.update([("BUILD_DATE", "date"), ("GIT_HASH", "hash")])
            watcher.start()
            targets = [
                new_ea(config.watch_dir / "EvilAngel - Carmela Clutch Fabulous Anal 3-Way", use_dir=True),
            ]
            prepare(targets, mock_poster, mock_response)
            wait_until_processed(config)
            watcher.stop()
            self.assertFalse(targets[0].file.exists())
            output_file = config.dest_dir / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4"
            validate_mp4_tags(self, output_file)
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)

    @patch("namer.metadataapi.__get_response_json_object")
    @patch("namer.namer.get_image")
    def test_name_parser_failure_with_startup_processing(self, mock_poster, mock_response):
        """
        Test the handle function works for a directory.
        """
        os.environ["NAMER_CONFIG"] = "./namer.cfg.sample"
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            config = make_locations(tempdir)
            config.prefer_dir_name_if_available = True
            config.write_namer_log = True
            config.min_file_size = 0
            config.name_parser = "{_site}{_sep}{_date}{_sep}{_ts}{_name}.{_ext}"
            watcher = create_watcher(config)
            os.environ.update([("BUILD_DATE", "date"), ("GIT_HASH", "hash")])
            targets = [
                new_ea(config.watch_dir / "EvilAngel - Carmela Clutch Fabulous Anal 3-Way", use_dir=True),
            ]
            prepare(targets, mock_poster, mock_response)
            # this tests startup processing.
            time.sleep(1)
            watcher.start()
            wait_until_processed(config)
            watcher.stop()
            self.assertFalse(targets[0].file.exists())
            output_file = (config.failed_dir / "EvilAngel - Carmela Clutch Fabulous Anal 3-Way")
            self.assertTrue(output_file.exists() and output_file.is_dir())
            validate_permissions(self, output_file, 775)
            self.assertEqual(len(list(config.failed_dir.iterdir())), 1)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            self.assertEqual(len(list(config.dest_dir.iterdir())), 0)

    @patch("namer.metadataapi.__get_response_json_object")
    @patch("namer.namer.get_image")
    @patch("namer.namer.get_trailer")
    def test_fetch_trailer_write_nfo_success(self, mock_trailer: MagicMock, mock_poster: MagicMock, mock_response: MagicMock):
        """
        Test the handle function works for a directory.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            config = make_locations(tempdir)
            config.prefer_dir_name_if_available = True
            config.min_file_size = 0
            config.write_namer_log = True
            config.min_file_size = 0
            config.write_nfo = True
            watcher = create_watcher(config)
            watcher.start()
            targets = [new_ea(config.watch_dir)]
            mock_response.return_value = targets[0].json_exact
            mock_trailer.return_value = "/some/location.mp4"
            mock_poster.return_value = targets[0].poster
            wait_until_processed(config)
            watcher.stop()
            self.assertFalse(targets[0].file.exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            output_file = config.dest_dir / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4"
            nfo_file = config.dest_dir / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.nfo"
            output = MP4(output_file)
            self.assertEqual(output.get("\xa9nam"), ["Carmela Clutch: Fabulous Anal 3-Way!"])
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)
            self.assertTrue(nfo_file.exists() and nfo_file.is_file() and nfo_file.stat().st_size != 0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
