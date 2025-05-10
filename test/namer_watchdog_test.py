"""
Test namer_watchdog.py
"""

import contextlib
import time
from typing import Any
import unittest
from pathlib import Path

from loguru import logger
from mutagen.mp4 import MP4

from namer.ffmpeg import FFMpeg
from namer.configuration import NamerConfig
from namer.watchdog import create_watcher, done_copying, retry_failed, MovieWatcher
from test import utils
from test.utils import Wait, new_ea, new_dorcel, validate_mp4_tags, validate_permissions, environment, sample_config, ProcessingTarget


def wait_until_processed(watcher: MovieWatcher, duration: int = 60):
    """
    Waits until all files have been moved out of watch/working dirs.
    """
    config = watcher.get_config()
    Wait().seconds(duration).checking(1).until(lambda: len(list(config.watch_dir.iterdir())) > 0 or len(list(config.work_dir.iterdir())) > 0).is_false()
    watcher.stop()


@contextlib.contextmanager
def make_watchdog_context(config: NamerConfig, targets=None):
    if targets is None:
        targets = []

    with environment(config) as (temp_dir, mock_tpdb, config):
        for target in targets:
            if target.file is None:
                target.setup(config.watch_dir)
        with create_watcher(config) as watcher:
            yield temp_dir, watcher, mock_tpdb


def remove_performer_genders(data: Any):
    single_scene = data['data']
    for json_performer in single_scene['performers']:
        if not json_performer['extra']:
            continue
        json_performer['extra']['gender'] = None


def remove_performers(data: Any):
    single_scene = data['data']
    single_scene['performers'] = []


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    def __init__(self, method_name='runTest'):
        super().__init__(method_name)

        if not utils.is_debugging():
            logger.remove()

    def test_done_copying_non_existent_file(self):
        """
        Test negatives.
        """
        non_path = Path('should_not_exist')
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
        targets: list[ProcessingTarget] = [new_ea(), new_ea(use_dir=False)]
        with make_watchdog_context(config, targets) as (temp_dir, watcher, fake_tpdb):
            wait_until_processed(watcher)
            self.assertFalse(targets[0].get_file().exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            output_file = config.dest_dir / 'Evil Angel' / 'Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! [WEBDL-240].mp4'
            output = MP4(output_file)
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])

            output_file2 = config.dest_dir / 'Evil Angel' / 'Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! [WEBDL-240](1).mp4'
            output2 = MP4(output_file2)
            self.assertEqual(output2.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)

    def test_handler_collisions_success_choose_best(self):
        """
        Test the handle function works for a directory.
        """
        okay = 'Big_Buck_Bunny_360_10s_2MB_h264.mp4'
        better = 'Big_Buck_Bunny_720_10s_2MB_h264.mp4'
        best = 'Big_Buck_Bunny_720_10s_2MB_h265.mp4'
        config = sample_config()
        config.prefer_dir_name_if_available = True
        config.write_namer_log = True
        config.min_file_size = 0
        config.preserve_duplicates = False
        config.max_desired_resolutions = -1
        config.desired_codec = ['hevc', 'h264']
        with make_watchdog_context(config) as (temp_dir, watcher, fake_tpdb):
            targets: list[ProcessingTarget] = [new_ea(config.watch_dir, mp4_file_name=okay), new_ea(config.watch_dir, use_dir=False, post_stem='2', mp4_file_name=better), new_ea(config.watch_dir, use_dir=False, post_stem='1', mp4_file_name=best)]
            wait_until_processed(watcher, 120)
            self.assertFalse(targets[0].get_file().exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            output_file = config.dest_dir / 'Evil Angel' / 'Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! [WEBDL-720p].mp4'
            self.assertEqual(MP4(output_file).get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])
            results = FFMpeg().ffprobe(output_file)
            self.assertIsNotNone(results)
            if results:
                stream = results.get_default_video_stream()
                self.assertIsNotNone(stream)
                if stream:
                    self.assertEqual(stream.height, 720)
                    self.assertEqual(stream.codec_name, 'hevc')
            output_file2 = config.dest_dir / 'Evil Angel' / 'Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! [WEBDL-720p](1).mp4'
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
        with make_watchdog_context(config) as (temp_dir, watcher, fake_tpdb):
            targets = [new_ea(config.watch_dir)]
            wait_until_processed(watcher)
            self.assertFalse(targets[0].get_file().exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            output_file = config.dest_dir / 'Evil Angel' / 'Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! [WEBDL-240].mp4'
            output = MP4(output_file)
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)

    def test_event_listener_success_conversion(self):
        """
        Test the handle function works for a directory.
        """
        config = sample_config()
        config.prefer_dir_name_if_available = True
        config.min_file_size = 0
        config.write_namer_log = True
        config.min_file_size = 0
        config.convert_container_to = 'mkv'
        with make_watchdog_context(config) as (temp_dir, watcher, fake_tpdb):
            targets = [new_ea(config.watch_dir)]
            wait_until_processed(watcher)
            self.assertFalse(targets[0].get_file().exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            output_file = config.dest_dir / 'Evil Angel' / 'Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! [WEBDL-240].mkv'
            self.assertTrue(output_file.exists())

    def test_handler_deeply_nested_success_no_dirname(self):
        """
        Test the handle function works for a directory.
        """
        config = sample_config()
        config.prefer_dir_name_if_available = False
        config.write_namer_log = True
        config.min_file_size = 0
        config.preserve_duplicates = True
        with make_watchdog_context(config) as (temp_dir, watcher, fake_tpdb):
            targets = [
                new_ea(config.watch_dir / 'deeper' / 'and_deeper', use_dir=False),
                new_ea(config.watch_dir, post_stem='number2', use_dir=False),
            ]
            wait_until_processed(watcher)
            self.assertFalse(targets[0].get_file().exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            output_file = config.dest_dir / 'Evil Angel' / 'Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! [WEBDL-240].mp4'
            validate_mp4_tags(self, output_file)
            self.assertTrue((output_file.parent / (output_file.stem + '_namer.json.gz')).exists())
            output_file2 = config.dest_dir / 'Evil Angel' / 'Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! [WEBDL-240](1).mp4'
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
        config.new_relative_path_name = '{site}/{site} - {date} - {name}/{site} - {date} - {name}.{ext}'
        with make_watchdog_context(config) as (temp_dir, watcher, fake_tpdb):
            targets = [
                new_ea(config.watch_dir / 'deeper' / 'and_deeper', use_dir=False),
            ]
            testfile = config.watch_dir / 'deeper' / 'testfile.txt'
            contents = 'Create a new text file!'
            with open(testfile, 'w', encoding='utf-8') as file:
                file.write(contents)
            wait_until_processed(watcher)
            self.assertFalse(targets[0].get_file().exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            output_file = config.dest_dir / 'EvilAngel' / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!' / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4'
            validate_mp4_tags(self, output_file)
            validate_permissions(self, output_file, 664)
            output_test_file = config.dest_dir / 'EvilAngel' / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!' / 'testfile.txt'
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
        config.new_relative_path_name = './{network}/' + config.new_relative_path_name
        with make_watchdog_context(config) as (temp_dir, watcher, fake_tpdb):
            targets = [
                new_ea(config.watch_dir / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way', use_dir=True),
            ]
            wait_until_processed(watcher)
            self.assertFalse(targets[0].get_file().exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            watcher.stop()
            output_file = config.dest_dir / 'GammaEnterprises' / 'Evil Angel' / 'Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! [WEBDL-240].mp4'
            validate_mp4_tags(self, output_file)
            validate_permissions(self, output_file, 600)
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)

    def test_handler_deeply_nested_success_missing_network(self):
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
        config.new_relative_path_name = './{network}/' + config.new_relative_path_name
        with make_watchdog_context(config) as (temp_dir, watcher, fake_tpdb):
            targets = [
                new_dorcel(config.watch_dir, use_dir=True),
            ]
            wait_until_processed(watcher)
            self.assertFalse(targets[0].get_file().exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            watcher.stop()
            output_file = config.dest_dir / 'Dorcel Club' / 'Dorcel Club - 2021-12-23 - Peeping Tom [WEBDL-240].mp4'
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
        config.new_relative_path_name = '{site} - {date} - {name}/{site} - {date} - {name} - {uuid} - {external_id} - ({resolution}).{ext}'
        with make_watchdog_context(config) as (temp_dir, watcher, fake_tpdb):
            targets = [
                new_ea(config.watch_dir / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way', use_dir=True),
            ]
            wait_until_processed(watcher)
            self.assertFalse(targets[0].get_file().exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            output_file = config.dest_dir / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!' / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! - scenes1678283 - 198543 - (240).mp4'
            validate_mp4_tags(self, output_file)
            validate_permissions(self, output_file, 600)
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)

    def test_handler_deeply_nested_success_bracked(self):
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
        config.new_relative_path_name = '{site} - {date} - {name}/{site} - {date} - {name} - {uuid} - {external_id} - ({resolution}).{ext}'
        with make_watchdog_context(config) as (temp_dir, watcher, fake_tpdb):
            targets = [
                new_ea(config.watch_dir / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! XXX [XvX]', post_stem='XXX [XvX]'),
            ]
            wait_until_processed(watcher)
            self.assertFalse(targets[0].get_file().exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            output_file = config.dest_dir / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!' / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! - scenes1678283 - 198543 - (240).mp4'
            validate_mp4_tags(self, output_file)
            validate_permissions(self, output_file, 600)
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)

    def test_handler_ignore(self):
        """
        Test the handle function works for a directory.
        """
        with make_watchdog_context(sample_config()) as (temp_dir, watcher, fake_tpdb):
            targets = [
                new_ea(watcher.get_config().watch_dir / '_UNPACK_stuff' / 'EvilAngel - Carmela Clutch Fabulous Anal 3-Way', use_dir=True),
            ]
            time.sleep(2)
            watcher.stop()
            self.assertTrue(targets[0].get_file().exists())

    def test_handler_failure(self):
        """
        Test the handle function works for a directory.
        """
        config = sample_config()
        config.write_namer_log = True
        config.del_other_files = False
        config.min_file_size = 0
        with make_watchdog_context(config) as (temp_dir, watcher, fake_tpdb):
            targets = [new_ea(config.watch_dir, use_dir=False, match=False)]
            wait_until_processed(watcher)
            self.assertFalse(targets[0].get_file().exists())
            relative = targets[0].get_file().relative_to(config.watch_dir)
            work_file = config.work_dir / relative
            self.assertFalse(work_file.exists())
            failed_file = config.failed_dir / relative
            self.assertTrue(failed_file.exists() and failed_file.is_file())
            failed_log_file = failed_file.parent / (failed_file.stem + '_namer.json.gz')
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
        config.name_parser = '{_site} - {_ts}{_name}.{_ext}'
        config.sites_with_no_date_info = ['evilangel']
        with make_watchdog_context(config) as (temp_dir, watcher, fake_tpdb):
            targets = [
                new_ea(config.watch_dir / 'EvilAngel - Carmela Clutch Fabulous Anal 3-Way', use_dir=True),
            ]
            wait_until_processed(watcher)
            self.assertFalse(targets[0].get_file().exists())
            output_file = config.dest_dir / 'Evil Angel' / 'Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! [WEBDL-240].mp4'
            validate_mp4_tags(self, output_file)
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)

    def test_missing_performers_gender_success(self):
        """
        Test files aren't lost when fields are missing.
        """
        config = sample_config()
        config.prefer_dir_name_if_available = True
        config.min_file_size = 0
        config.write_namer_log = True
        config.min_file_size = 0
        config.new_relative_path_name = '{performers}/{site} - {date} - {name}.{ext}'
        with make_watchdog_context(config) as (temp_dir, watcher, fake_tpdb):
            remove_performer_genders(fake_tpdb._scenes['ea.full.json'])
            targets = [new_ea(config.watch_dir)]
            wait_until_processed(watcher)
            self.assertFalse(targets[0].get_file().exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            output_file = config.dest_dir / 'Carmela Clutch, Francesca Le' / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4'
            self.assertTrue(output_file.is_file())
            output = MP4(output_file)
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)

    def test_missing_performers_success(self):
        """
        Test files aren't lost when fields are missing.
        """
        config = sample_config()
        config.prefer_dir_name_if_available = True
        config.min_file_size = 0
        config.write_namer_log = True
        config.min_file_size = 0
        config.new_relative_path_name = '{performers}/{site} - {date} - {name}.{ext}'
        with make_watchdog_context(config) as (temp_dir, watcher, fake_tpdb):
            remove_performers(fake_tpdb._scenes['ea.full.json'])
            targets = [new_ea(config.watch_dir)]
            wait_until_processed(watcher)
            self.assertFalse(targets[0].get_file().exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            output_file = config.dest_dir / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4'
            self.assertTrue(output_file.is_file())
            output = MP4(output_file)
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)

    def test_name_parser_failure_with_startup_processing(self):
        """
        Test the handle function works for a directory.
        """
        config = sample_config()
        config.prefer_dir_name_if_available = True
        config.write_namer_log = True
        config.min_file_size = 0
        config.name_parser = '{_site}{_sep}{_date}{_sep}{_ts}{_name}.{_ext}'
        targets = [
            new_ea(relative='EvilAngel - Carmela Clutch Fabulous Anal 3-Way/', use_dir=True),
        ]
        with make_watchdog_context(config, targets) as (temp_dir, watcher, fake_tpdb):
            wait_until_processed(watcher)
            self.assertFalse(targets[0].get_file().exists())
            output_file = config.failed_dir / 'EvilAngel - Carmela Clutch Fabulous Anal 3-Way'
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
        targets = [new_ea()]
        with make_watchdog_context(config, targets) as (temp_dir, watcher, fake_tpdb):
            wait_until_processed(watcher)
            self.assertFalse(targets[0].get_file().exists())
            self.assertEqual(len(list(config.work_dir.iterdir())), 0)
            output_file = config.dest_dir / 'Evil Angel' / 'Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! [WEBDL-240].mp4'
            nfo_file = config.dest_dir / 'Evil Angel' / 'Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! [WEBDL-240].nfo'
            output = MP4(output_file)
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])
            self.assertEqual(len(list(config.failed_dir.iterdir())), 0)
            self.assertEqual(len(list(config.watch_dir.iterdir())), 0)
            self.assertTrue(nfo_file.exists() and nfo_file.is_file() and nfo_file.stat().st_size != 0)


if __name__ == '__main__':
    unittest.main()
