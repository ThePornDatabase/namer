"""
Test namer_watchdog.py
"""
from pathlib import Path
import unittest
from unittest.mock import patch
import logging
import tempfile
import shutil
from watchdog.events import FileSystemEvent, FileSystemMovedEvent
from mutagen.mp4 import MP4
from namer_dirscanner_test import prepare_workdir
from namer_mutagen_test import validate_mp4_tags
from namer_test import new_ea, prepare
from namer_types import default_config
from namer_watchdog import MovieEventHandler, handle

class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_handler_collisions_success(self, mock_poster, mock_response):
        """
        Test the handle function works for a directory.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)

            config = default_config()
            config.prefer_dir_name_if_available = True
            config.watch_dir = tempdir / 'watch'
            config.watch_dir.mkdir()
            config.work_dir = tempdir / 'work'
            config.work_dir.mkdir()
            config.dest_dir = tempdir / 'dest'
            config.dest_dir.mkdir()
            config.failed_dir = tempdir / 'failed'
            config.failed_dir.mkdir()
            targets = [new_ea(config.watch_dir),new_ea(config.watch_dir,use_dir=False)]
            prepare(targets, mock_poster, mock_response)
            handle(Path(targets[0].file), config)
            handle(Path(targets[1].file), config)
            self.assertFalse(targets[0].file.exists())
            self.assertEqual(len(list(config.work_dir.iterdir())),0)
            outputfile = ( config.dest_dir / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!' /
                'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4')
            output = MP4(outputfile)
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])

            outputfile2 = ( config.dest_dir / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!' /
                'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!(1).mp4')
            output2 = MP4(outputfile2)
            self.assertEqual(output2.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])



    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_eventlisterner_success(self, mock_poster, mock_response):
        """
        Test the handle function works for a directory.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)

            config = default_config()
            config.prefer_dir_name_if_available = True
            config.watch_dir = tempdir / 'watch'
            config.watch_dir.mkdir()
            config.work_dir = tempdir / 'work'
            config.work_dir.mkdir()
            config.dest_dir = tempdir / 'dest'
            config.dest_dir.mkdir()
            config.failed_dir = tempdir / 'failed'
            config.failed_dir.mkdir()
            config.min_file_size=0
            targets = [new_ea(config.watch_dir)]
            prepare(targets, mock_poster, mock_response)

            moviehandler = MovieEventHandler(config)
            moviehandler.on_created(FileSystemEvent(Path(targets[0].file)))

            self.assertFalse(targets[0].file.exists())
            self.assertEqual(len(list(config.work_dir.iterdir())),0)
            outputfile = ( config.dest_dir / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!' /
                'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4')
            output = MP4(outputfile)
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])


    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_handler_deeply_nested_success(self, mock_poster, mock_response):
        """
        Test the handle function works for a directory.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)

            config = default_config()
            config.prefer_dir_name_if_available = False
            config.watch_dir = tempdir / 'watch'
            config.watch_dir.mkdir()
            config.work_dir = tempdir / 'work'
            config.work_dir.mkdir()
            config.dest_dir = tempdir / 'dest'
            config.dest_dir.mkdir()
            config.failed_dir = tempdir / 'failed'
            config.failed_dir.mkdir()

            targets = [
                new_ea(config.watch_dir / "deeper" / "and_deeper", use_dir=False),
                new_ea(config.watch_dir,post_stem="number2", use_dir=False)
            ]
            prepare(targets, mock_poster, mock_response)
            handle(Path(targets[0].file), config)
            handle(Path(targets[1].file.parent.parent), config)
            self.assertFalse(targets[0].file.exists())
            self.assertEqual(len(list(config.work_dir.iterdir())),0)
            outputfile = ( config.dest_dir / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!' /
                'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4')
            validate_mp4_tags(self, outputfile)
            outputfile2 = ( config.dest_dir / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!' /
                'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!(1).mp4')
            validate_mp4_tags(self, outputfile2)

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_handler_failure(self, mock_poster, mock_response):
        """
        Test the handle function works for a directory.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(prepare_workdir(tmpdir))
            mock_response.return_value = "{}"
            input_dir = tempdir / 'test'
            poster = tempdir / 'test' / 'poster.png'
            shutil.move(poster, poster)

            mock_poster.return_value = tempdir / 'poster.png'
            config = default_config()
            config.watch_dir = tempdir / 'watch'
            config.watch_dir.mkdir()
            config.work_dir = tempdir / 'work'
            config.work_dir.mkdir()
            config.dest_dir = tempdir / 'dest'
            config.dest_dir.mkdir()
            config.failed_dir = tempdir / 'failed'
            config.failed_dir.mkdir()
            config.min_file_size = 0
            targetfile = (tempdir / 'watch' /
                "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p")
            input_dir.rename(targetfile)

            handler = MovieEventHandler(config)
            handler.process(targetfile)

            self.assertFalse(targetfile.exists())
            self.assertFalse(
                (config.work_dir / "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p" ).exists())
            outputfile = (tempdir / 'failed' /
                'DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p')
            self.assertTrue(outputfile.exists() and outputfile.is_dir())

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    unittest.main()
