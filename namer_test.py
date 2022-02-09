"""
Fully test namer.py
"""
import shutil
import unittest
from distutils.dir_util import copy_tree
from unittest.mock import patch
import os
import tempfile
from mutagen.mp4 import MP4
from namer_metadataapi_test import readfile
from namer import main
from namer_dirscanner_test import prepare_workdir

ROOT_DIR = './test/'

class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    current=os.path.dirname(os.path.abspath(__file__))

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_writing_metadata_file(self, mock_poster, mock_response):
        """
        test namer main method renames and tags in place when -f (video file) is passed
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            prepare_workdir(tmpdir)
            path = os.path.join(tmpdir,'test',"DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.json")
            response  = readfile(path)
            mock_response.return_value = response
            mock_poster.return_value = os.path.join(tmpdir,'test',"poster.png")
            mp4_file = os.path.join(tmpdir, 'test', "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4")
            targetfile = os.path.join(tmpdir, 'test',
                "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p.mp4")
            os.rename(mp4_file, targetfile)
            main(['-f',targetfile])
            output = MP4(os.path.join(os.path.dirname(targetfile), 'DorcelClub - 2021-12-23 - Peeping Tom.mp4'))
            self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_writing_metadata_dir(self, mock_poster, mock_response):
        """
        test namer main method renames and tags in place when -d (directory) is passed
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            prepare_workdir(tmpdir)
            path = os.path.join(tmpdir,'test',"DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.json")
            response  = readfile(path)
            mock_response.return_value = response
            input_dir = os.path.join(tmpdir, 'test')
            targetfile = os.path.join(tmpdir, "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p")
            os.rename(input_dir, targetfile)
            mock_poster.return_value = os.path.join(targetfile,"poster.png")

            main(['-d',targetfile])

            output = MP4(os.path.join(tmpdir, "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p",
                    'DorcelClub - 2021-12-23 - Peeping Tom.mp4'))
            self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_writing_metadata_all_dirs(self, mock_poster, mock_response):
        """
        Test multiple directories are processed when -d (directory) and -m are passed.
        Process all subdirs of -d.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            prepare_workdir(tmpdir)
            path = os.path.join(tmpdir,'test',"DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.json")
            response  = readfile(path)
            mock_response.return_value = response
            input_directory = os.path.join(tmpdir, 'test')
            targetfile = os.path.join(tmpdir, "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p")
            os.rename(input_directory, targetfile)
            copy_tree(targetfile, targetfile+"2")
            mock_poster.side_effect = [os.path.join(targetfile,"poster.png"),os.path.join(targetfile+"2","poster.png")]
            main(['-d',os.path.dirname(targetfile),'-m'])
            output = MP4(os.path.join(targetfile, 'DorcelClub - 2021-12-23 - Peeping Tom.mp4'))
            self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])
            output = MP4(os.path.join(targetfile+"2", 'DorcelClub - 2021-12-23 - Peeping Tom.mp4'))
            self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_writing_metadata_all_dirs_files(self, mock_poster, mock_response):
        """
        Test multiple directories are processed when -d (directory) and -m are passed.
        Process all subdirs of -d.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            prepare_workdir(tmpdir)
            path = os.path.join(tmpdir,'test',"DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.json")
            response1 = readfile(path)
            path2 = os.path.join(tmpdir,'test',"response.json")
            response2 = readfile(path2)
            mock_response.side_effect = [response1, response2]
            os.makedirs(os.path.join(tmpdir, 'targetpath'))
            input_file = os.path.join(tmpdir, 'test', 'Site.22.01.01.painful.pun.XXX.720p.xpost.mp4')
            targetfile1 = os.path.join(tmpdir,
                'targetpath', "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p.mp4")
            os.rename(input_file, targetfile1)
            targetfile2 = os.path.join(tmpdir, 'targetpath', "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way.mp4")
            shutil.copy(targetfile1, targetfile2)
            shutil.copy(os.path.join(tmpdir,'test', "poster.png"), os.path.splitext(targetfile1)[0]+"_poster_in.png")
            shutil.copy(os.path.join(tmpdir,'test', "poster.png"), os.path.splitext(targetfile2)[0]+"_poster_in.png")
            mock_poster.side_effect = [os.path.splitext(targetfile1)[0]+"_poster_in.png",os.path.splitext(targetfile2)[0]+"_poster_in.png"]
            main(['-d',os.path.dirname(targetfile1),'-m'])
            output = MP4(os.path.join(tmpdir, 'targetpath', 'DorcelClub - 2021-12-23 - Peeping Tom.mp4'))
            self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])
            output = MP4(os.path.join(tmpdir, 'targetpath', 'EvilAngel - 2022-01-03 - Carmela Clutch: Fabulous Anal 3-Way!.mp4'))
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])

if __name__ == '__main__':
    unittest.main()
    