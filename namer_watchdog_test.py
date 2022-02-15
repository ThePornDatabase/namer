"""
Test namer_watchdog.py
"""
from pathlib import Path
import unittest
from unittest.mock import patch
import logging
import tempfile
import shutil
from mutagen.mp4 import MP4
from namer_dirscanner_test import prepare_workdir
from namer_types import default_config
from namer_watchdog import MovieEventHandler, handle

class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_handler_success(self, mock_poster, mock_response):
        """
        Test the handle function works for a directory.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(prepare_workdir(tmpdir))
            path = tempdir / 'test' / "dc.json"
            response = path.read_text()
            mock_response.return_value = response
            input_dir = tempdir / 'test'
            poster = input_dir / 'poster.png'
            shutil.move(poster,  tempdir / 'poster.png')

            targetfile = tempdir / 'watch' / "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p"
            targetfile.parent.mkdir()
            shutil.move(input_dir, targetfile)
            mock_poster.return_value = Path(tmpdir) / 'poster.png'
            config = default_config()
            config.watch_dir = tempdir / 'watch'
            config.work_dir = tempdir / 'work'
            config.work_dir.mkdir()
            config.dest_dir = tempdir / 'dest'
            config.dest_dir.mkdir()
            config.failed_dir = tempdir / 'failed'
            config.failed_dir.mkdir()

            handle(Path(targetfile), config)

            self.assertFalse(targetfile.exists())
            self.assertFalse(
                (config.work_dir / "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p" ).exists())
            outputfile = ( config.dest_dir / 'DorcelClub - 2021-12-23 - Peeping Tom' /
                'DorcelClub - 2021-12-23 - Peeping Tom.mp4')
            output = MP4(outputfile)
            self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])


    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_handler_deeply_nested_success(self, mock_poster, mock_response):
        """
        Test the handle function works for a directory.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(prepare_workdir(tmpdir))
            path = tempdir / 'test' / "dc.json"
            response = path.read_text()
            mock_response.return_value = response
            input_dir = tempdir / 'test'
            poster = input_dir / 'poster.png'
            shutil.move(poster,  tempdir / 'poster.png')

            targetfile = ( tempdir / 'watch' / "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p"
                / "unpack" )
            targetfile.parent.parent.mkdir()
            targetfile.parent.mkdir()
            targetfile.mkdir()
            shutil.move(input_dir, targetfile)
            mock_poster.return_value = Path(tmpdir) / 'poster.png'
            config = default_config()
            config.watch_dir = tempdir / 'watch'
            config.work_dir = tempdir / 'work'
            config.work_dir.mkdir()
            config.dest_dir = tempdir / 'dest'
            config.dest_dir.mkdir()
            config.failed_dir = tempdir / 'failed'
            config.failed_dir.mkdir()

            handle(Path(targetfile), config)
            outputfile = ( config.dest_dir / 'DorcelClub - 2021-12-23 - Peeping Tom' /
                'DorcelClub - 2021-12-23 - Peeping Tom.mp4')

            output = MP4(outputfile)
            self.assertFalse(targetfile.parent.exists())
            self.assertFalse(
                (config.work_dir / "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p" ).exists())
            self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])


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
