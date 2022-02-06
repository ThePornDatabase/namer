"""
Test namer_watchdog.py
"""
import os
import unittest
from unittest.mock import patch
import logging
import tempfile
import shutil
from mutagen.mp4 import MP4
from namer_dirscanner_test import prepare_workdir
from namer_types import default_config
from namer_watchdog import handle
from namer_moviexml import readfile


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    current = os.path.dirname(os.path.abspath(__file__))

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_handler_success(self, mock_poster, mock_response):
        """
        Test the handle function works for a directory.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            prepare_workdir(tmpdir)
            path = os.path.join(tmpdir, 'test', "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.json")
            response = readfile(path)
            mock_response.return_value = response
            input_dir = os.path.join(tmpdir, 'test')
            poster = os.path.join(tmpdir, 'test', 'poster.png')
            shutil.move(poster,  os.path.join(tmpdir, 'poster.png'))

            targetfile = os.path.join(tmpdir, 'watch',
                "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p")
            os.mkdir(os.path.join(tmpdir, 'watch'))
            shutil.move(input_dir, targetfile)
            mock_poster.return_value = os.path.join(tmpdir, 'poster.png')
            config = default_config()
            os.mkdir(os.path.join(tmpdir, 'work'))

            config.watch_dir = os.path.join(tmpdir, 'watch')
            config.work_dir = os.path.join(tmpdir, 'work')
            config.dest_dir = os.path.join(tmpdir, 'dest')
            os.mkdir(os.path.join(tmpdir, 'dest'))
            config.failed_dir = os.path.join(tmpdir, 'failed')
            os.mkdir(os.path.join(tmpdir, 'failed'))

            handle(targetfile, config)
            outputfile = os.path.join(tmpdir, 'dest',
                'DorcelClub - 2021-12-23 - Peeping Tom','DorcelClub - 2021-12-23 - Peeping Tom.mp4')

            output = MP4(outputfile)
            self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_handler_failure(self, mock_poster, mock_response):
        """
        Test the handle function works for a directory.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            prepare_workdir(tmpdir)
            mock_response.return_value = "{}"
            input_dir = os.path.join(tmpdir, 'test')
            poster = os.path.join(tmpdir, 'test', 'poster.png')
            shutil.move(poster,  os.path.join(tmpdir, 'poster.png'))

            targetfile = os.path.join(tmpdir, 'watch',
                "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p")
            os.mkdir(os.path.join(tmpdir, 'watch'))
            shutil.move(input_dir, targetfile)
            mock_poster.return_value = os.path.join(tmpdir, 'poster.png')
            config = default_config()
            os.mkdir(os.path.join(tmpdir, 'work'))

            config.watch_dir = os.path.join(tmpdir, 'watch')
            config.work_dir = os.path.join(tmpdir, 'work')
            config.dest_dir = os.path.join(tmpdir, 'dest')
            os.mkdir(os.path.join(tmpdir, 'dest'))
            config.failed_dir = os.path.join(tmpdir, 'failed')
            os.mkdir(os.path.join(tmpdir, 'failed'))

            handle(targetfile, config)
            outputfile = os.path.join(tmpdir, 'failed',
                'DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p')

            self.assertTrue(os.path.isdir(outputfile))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    unittest.main()
