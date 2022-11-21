"""
Test namer_watchdog.py
"""
import contextlib
import logging
import time
import unittest
from pathlib import Path

from mutagen.mp4 import MP4

from namer.ffmpeg import ffprobe
from namer.configuration import NamerConfig
from namer.watchdog import create_watcher, done_copying, retry_failed, MovieWatcher
from test.utils import Wait, new_ea, validate_mp4_tags, validate_permissions, environment, sample_config


def wait_until_processed(watcher: MovieWatcher):
    """
    Waits until all files have been moved out of watch/working dirs.
    """
    config = watcher.getConfig()
    Wait().until(lambda: len(list(config.watch_dir.iterdir())) > 0 or len(list(config.work_dir.iterdir())) > 0).isFalse()
    watcher.stop()


@contextlib.contextmanager
def make_watchdog_context(config: NamerConfig):
    with environment(config) as (tempdir, mock_tpdb, config):
        with create_watcher(config) as watcher:
            yield tempdir, watcher, mock_tpdb


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

    def test_handler_collisions_success(self):
        """
        Test the handle function works for a directory.
        """
        config = sample_config()
        config.prefer_dir_name_if_available = True
        config.write_namer_log = True
        config.min_file_size = 0
        with make_watchdog_context(config) as (tempdir, watcher, fakeTPDB):
            targets = [
                new_ea(config.watch_dir),
                new_ea(config.watch_dir, use_dir=False)
            ]
            wait_until_processed(watcher)
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

    def test_handler_collisions_success_choose_best(self):
        """
        Test the handle function works for a directory.
        """
        okay = "Big_Buck_Bunny_360_10s_2MB_h264.mp4"
        better = "Big_Buck_Bunny_720_10s_2MB_h264.mp4"
        best = "Big_Buck_Bunny_720_10s_2MB_h265.mp4"
        config = sample_config()
        config.prefer_dir_name_if_available = True
        config.write_namer_log = True
        config.min_file_size = 0
        config.preserve_duplicates = False
        config.max_desired_resolutions = -1
        config.desired_codec = ["hevc", "h264"]
        with make_watchdog_context(config) as (tempdir, watcher, fakeTPDB):
            targets = [
                new_ea(config.watch_dir, mp4_file_name=okay),
                new_ea(config.watch_dir, use_dir=False, post_stem="2", mp4_file_name=better),
                new_ea(config.watch_dir, use_dir=False, post_stem="1", mp4_file_name=best)
            ]
            wait_until_processed(watcher)
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

    def test_event_listener_success(self):
        """
        Test the handle function works for a directory.
        """
        config = sample_config()
        config.prefer_dir_name_if_available = True
        config.min_file_size = 0
        config.write_namer_log = True
        config.min_file_size = 0
        with make_watchdog_context(config) as (tempdir, watcher, fakeTPDB):
            targets = [new_ea(config.watch_dir)]
            wait_until_processed(watcher)
            self.assertFalse(targets[0].file.exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            output_file = config.dest_dir / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4"
            output = MP4(output_file)
            self.assertEqual(output.get("\xa9nam"), ["Carmela Clutch: Fabulous Anal 3-Way!"])
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)

    def test_handler_deeply_nested_success_no_dirname(self):
        """
        Test the handle function works for a directory.
        """
        config = sample_config()
        config.prefer_dir_name_if_available = False
        config.write_namer_log = True
        config.min_file_size = 0
        config.preserve_duplicates = True
        with make_watchdog_context(config) as (tempdir, watcher, fakeTPDB):
            targets = [
                new_ea(config.watch_dir / "deeper" / "and_deeper", use_dir=False),
                new_ea(config.watch_dir, post_stem="number2", use_dir=False),
            ]
            wait_until_processed(watcher)
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

    def test_handler_deeply_nested_success_no_dirname_extra_files(self):
        """
        Test the handle function works for a directory.
        """
        config = sample_config()
        config.prefer_dir_name_if_available = False
        config.write_namer_log = True
        config.min_file_size = 0
        config.del_other_files = False
        config.new_relative_path_name = "{site}/{site} - {date} - {name}/{site} - {date} - {name}.{ext}"
        with make_watchdog_context(config) as (tempdir, watcher, fakeTPDB):
            targets = [
                new_ea(config.watch_dir / "deeper" / "and_deeper", use_dir=False),
            ]
            testfile = config.watch_dir / "deeper" / "testfile.txt"
            contents = "Create a new text file!"
            with open(testfile, "w", encoding="utf-8") as file:
                file.write(contents)
            wait_until_processed(watcher)
            self.assertFalse(targets[0].file.exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            output_file = config.dest_dir / "EvilAngel" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4"
            validate_mp4_tags(self, output_file)
            validate_permissions(self, output_file, 664)
            output_test_file = config.dest_dir / "EvilAngel" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" / "testfile.txt"
            self.assertEqual(output_test_file.read_text(), contents)
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)

    def test_handler_deeply_nested_success(self):
        """
        Test the handle function works for a directory.
        """
        config = sample_config()
        config.prefer_dir_name_if_available = True
        config.write_namer_log = True
        config.del_other_files = False
        config.min_file_size = 0
        config.set_dir_permissions = None
        config.set_file_permissions = None
        with make_watchdog_context(config) as (tempdir, watcher, fakeTPDB):
            targets = [
                new_ea(config.watch_dir / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way", use_dir=True),
            ]
            wait_until_processed(watcher)
            self.assertFalse(targets[0].file.exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            watcher.stop()
            output_file = config.dest_dir / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4"
            validate_mp4_tags(self, output_file)
            validate_permissions(self, output_file, 600)
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)

    def test_handler_deeply_nested_success_custom_location(self):
        """
        Test the handle function works for a directory.
        """
        config = sample_config()
        config.prefer_dir_name_if_available = True
        config.write_namer_log = True
        config.del_other_files = False
        config.min_file_size = 0
        config.set_dir_permissions = None
        config.set_file_permissions = None
        config.new_relative_path_name = "{site} - {date} - {name}/{site} - {date} - {name} - {uuid} - {external_id} - ({resolution}).{ext}"
        with make_watchdog_context(config) as (tempdir, watcher, fakeTPDB):
            targets = [
                new_ea(config.watch_dir / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way", use_dir=True),
            ]
            wait_until_processed(watcher)
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
        with make_watchdog_context(sample_config()) as (tempdir, watcher, fakeTPDB):
            targets = [
                new_ea(watcher.getConfig().watch_dir / "_UNPACK_stuff" / "EvilAngel - Carmela Clutch Fabulous Anal 3-Way", use_dir=True),
            ]
            time.sleep(2)
            watcher.stop()
            self.assertTrue(targets[0].file.exists())

    def test_handler_failure(self):
        """
        Test the handle function works for a directory.
        """
        config = sample_config()
        config.write_namer_log = True
        config.del_other_files = False
        config.min_file_size = 0
        with make_watchdog_context(config) as (tempdir, watcher, fakeTPDB):
            targets = [new_ea(config.watch_dir, use_dir=False, match=False)]
            wait_until_processed(watcher)
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

    def test_name_parser_success(self):
        """
        Test the handle function works for a directory.
        """
        config = sample_config()
        config.prefer_dir_name_if_available = True
        config.write_namer_log = True
        config.min_file_size = 0
        config.name_parser = "{_site} - {_ts}{_name}.{_ext}"
        config.sites_with_no_date_info = ["evilangel"]
        with make_watchdog_context(config) as (tempdir, watcher, fakeTPDB):
            targets = [
                new_ea(config.watch_dir / "EvilAngel - Carmela Clutch Fabulous Anal 3-Way", use_dir=True),
            ]
            wait_until_processed(watcher)
            self.assertFalse(targets[0].file.exists())
            output_file = config.dest_dir / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4"
            validate_mp4_tags(self, output_file)
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)

    def test_name_parser_failure_with_startup_processing(self):
        """
        Test the handle function works for a directory.
        """
        config = sample_config()
        config.prefer_dir_name_if_available = True
        config.write_namer_log = True
        config.min_file_size = 0
        config.name_parser = "{_site}{_sep}{_date}{_sep}{_ts}{_name}.{_ext}"
        with environment(config) as (tempdir, mock_tpdb, config):
            targets = [
                new_ea(config.watch_dir / "EvilAngel - Carmela Clutch Fabulous Anal 3-Way", use_dir=True),
            ]
            with create_watcher(config) as watcher:
                wait_until_processed(watcher)
                self.assertFalse(targets[0].file.exists())
                output_file = (config.failed_dir / "EvilAngel - Carmela Clutch Fabulous Anal 3-Way")
                self.assertTrue(output_file.exists() and output_file.is_dir())
                validate_permissions(self, output_file, 775)
                self.assertEqual(len(list(config.failed_dir.iterdir())), 1)
                self.assertEqual(len(list(config.watch_dir.iterdir())), 0)
                self.assertEqual(len(list(config.work_dir.iterdir())), 0)
                self.assertEqual(len(list(config.dest_dir.iterdir())), 0)

    def test_fetch_trailer_write_nfo_success(self):
        """
        Test the handle function works for a directory.
        """
        config = sample_config()
        config.prefer_dir_name_if_available = True
        config.min_file_size = 0
        config.write_namer_log = True
        # TODO:
        # config.trailer_location = "Trailers/trailer.{ext}"
        config.min_file_size = 0
        config.write_nfo = True
        with make_watchdog_context(config) as (tempdir, watcher, fakeTPDB):
            targets = [new_ea(config.watch_dir)]
            wait_until_processed(watcher)
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
