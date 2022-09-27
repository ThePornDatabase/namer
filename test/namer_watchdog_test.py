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

from mutagen.mp4 import MP4

from namer.ffmpeg import ffprobe
from namer.configuration import NamerConfig
from namer.watchdog import create_watcher, done_copying, retry_failed
from test.utils import Wait, new_ea, prepare, sample_config, validate_mp4_tags, validate_permissions


def make_locations(tempdir: Path) -> NamerConfig:
    """
    Make temp testing dirs.
    """
    config = sample_config()
    config.watch_dir = tempdir / "watch"
    config.watch_dir.mkdir(parents=True, exist_ok=True)
    config.work_dir = tempdir / "work"
    config.work_dir.mkdir(parents=True, exist_ok=True)
    config.dest_dir = tempdir / "dest"
    config.dest_dir.mkdir(parents=True, exist_ok=True)
    config.failed_dir = tempdir / "failed"
    config.failed_dir.mkdir(parents=True, exist_ok=True)
    config.del_other_files = True
    config.extra_sleep_time = 1
    return config


def wait_until_processed(config: NamerConfig):
    """
    Waits until all files have been moved out of watch/working dirs.
    """
    Wait().until(lambda: len(list(config.watch_dir.iterdir())) > 0 or len(list(config.work_dir.iterdir())) > 0).isFalse()


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
    def test_handler_collisions_success_choose_best(self, mock_poster, mock_response):
        """
        Test the handle function works for a directory.
        """

        okay = "Big_Buck_Bunny_360_10s_2MB_h264.mp4"
        better = "Big_Buck_Bunny_720_10s_2MB_h264.mp4"
        best = "Big_Buck_Bunny_720_10s_2MB_h265.mp4"

        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            config = make_locations(tempdir)
            config.prefer_dir_name_if_available = True
            config.write_namer_log = True
            config.min_file_size = 0
            config.preserve_duplicates = False
            config.max_desired_resolutions = -1
            config.desired_codec = ["HEVC", "H264"]
            watcher = create_watcher(config)
            watcher.start()
            targets = [
                new_ea(config.watch_dir, mp4_file_name=okay),
                new_ea(config.watch_dir, use_dir=False, post_stem="2", mp4_file_name=better),
                new_ea(config.watch_dir, use_dir=False, post_stem="1", mp4_file_name=best)
            ]
            prepare(targets, mock_poster, mock_response)
            wait_until_processed(config)
            watcher.stop()
            self.assertFalse(targets[0].file.exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            output_file = config.dest_dir / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4"
            self.assertEqual(MP4(output_file).get("\xa9nam"), ["Carmela Clutch: Fabulous Anal 3-Way!"])
            results = ffprobe(output_file)
            self.assertIsNotNone(results)
            if results:
                stream = results.get_default_video_stream()
                self.assertIsNotNone(stream)
                if stream:
                    self.assertEqual(stream.height, 720)
                    self.assertEqual(stream.codec_name, "hevc")
            output_file2 = config.dest_dir / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!(1).mp4"
            self.assertFalse(output_file2.exists())

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
            self.assertTrue((output_file.parent / (output_file.stem + "_namer.json.gz")).exists())
            output_file2 = config.dest_dir / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!(1).mp4"
            validate_mp4_tags(self, output_file2)
            validate_permissions(self, output_file2, 664)
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)

    @patch("namer.metadataapi.__get_response_json_object")
    @patch("namer.namer.get_image")
    def test_handler_deeply_nested_success_no_dirname_extra_files(self, mock_poster, mock_response):
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
            config.del_other_files = False
            config.new_relative_path_name = "{site}/{site} - {date} - {name}/{site} - {date} - {name}.{ext}"
            watcher = create_watcher(config)
            watcher.start()
            targets = [
                new_ea(config.watch_dir / "deeper" / "and_deeper", use_dir=False),
            ]
            prepare(targets, mock_poster, mock_response)
            testfile = config.watch_dir / "deeper" / "testfile.txt"
            contents = "Create a new text file!"
            with open(testfile, "w", encoding="utf-8") as file:
                file.write(contents)
            wait_until_processed(config)
            watcher.stop()
            self.assertFalse(targets[0].file.exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            output_file = config.dest_dir / "EvilAngel" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4"
            validate_mp4_tags(self, output_file)
            validate_permissions(self, output_file, 664)
            output_test_file = config.dest_dir / "EvilAngel" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" / "testfile.txt"
            self.assertEqual(output_test_file.read_text(), contents)
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

    @patch("namer.metadataapi.__get_response_json_object")
    @patch("namer.namer.get_image")
    def test_handler_deeply_nested_success_custom_location(self, mock_poster, mock_response):
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
            config.new_relative_path_name = "{site} - {date} - {name}/{site} - {date} - {name} - {uuid} - {external_id} - ({resolution}).{ext}"
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
            output_file = config.dest_dir / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! - scenes1678283 - 198543 - (240).mp4"
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
            failed_log_file = failed_file.parent / (failed_file.stem + "_namer.json.gz")
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
            config.sites_with_no_date_info = ["evilangel"]
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
