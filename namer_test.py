"""
Fully test namer.py
"""
from dataclasses import dataclass
from pathlib import Path
import shutil
import unittest
from distutils.dir_util import copy_tree
from unittest.mock import patch
import os
import tempfile
from mutagen.mp4 import MP4
from namer import main
from namer_dirscanner_test import prepare_workdir

ROOT_DIR = './test/'

@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class ProcessingTarget:
    """
    Test data.
    """
    file: Path
    json: str
    poster: Path
    expect_match: bool

class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    current=os.path.dirname(os.path.abspath(__file__))

    def prep_dc_match(tempdir: Path, forMatching: Path, mock_poster, mock_response, success:bool = True):
        jsonfile = tempdir / 'test' / "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.json"
        jsontext = jsonfile.read_text()
        mp4_file = tempdir / 'test' / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4"
        shutil.copy(mp4_file, tempdir)


    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_writing_metadata_file(self, mock_poster, mock_response):
        """
        test namer main method renames and tags in place when -f (video file) is passed
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(prepare_workdir(tmpdir))
            path = tempdir / 'test' / "dc.json"
            mock_response.return_value = path.read_text()
            mock_poster.return_value = tempdir / 'test' / "poster.png"
            mp4_file = tempdir / 'test' / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4"
            targetfile = tempdir / 'test' / "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p.mp4"
            mp4_file.rename(targetfile)
            main(['-f',targetfile])
            output = MP4(targetfile.parent / 'DorcelClub - 2021-12-23 - Peeping Tom.mp4')
            self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_writing_metadata_dir(self, mock_poster, mock_response):
        """
        test namer main method renames and tags in place when -d (directory) is passed
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(prepare_workdir(tmpdir))
            path = tempdir / 'test' / "dc.json"
            response  = path.read_text()
            mock_response.return_value = response
            input_dir = tempdir / 'test'
            targetfile = tempdir / "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p"
            input_dir.rename(targetfile)
            mock_poster.return_value = targetfile / "poster.png"

            main(['-d',targetfile])

            output = MP4(tempdir / "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p" /
                    'DorcelClub - 2021-12-23 - Peeping Tom.mp4')
            self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_writing_metadata_all_dirs(self, mock_poster, mock_response):
        """
        Test multiple directories are processed when -d (directory) and -m are passed.
        Process all subdirs of -d.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(prepare_workdir(tmpdir))
            path = tempdir / 'test' / "dc.json"
            response  = path.read_text()
            mock_response.return_value = response
            input_directory = tempdir / 'test'
            targetfile = tempdir / "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p"
            input_directory.rename(targetfile)
            target2 = targetfile.parent / (targetfile.name+"2")
            copy_tree(str(targetfile), str(target2) )
            mock_poster.side_effect = [ targetfile / "poster.png" , target2 / "poster.png"]
            main(['-d',targetfile.parent,'-m'])
            output = MP4(targetfile / 'DorcelClub - 2021-12-23 - Peeping Tom.mp4')
            self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])
            output = MP4(target2 / 'DorcelClub - 2021-12-23 - Peeping Tom.mp4')
            self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_writing_metadata_conflict_files(self, mock_poster, mock_response):
        """
        Test multiple files are processed when -d (directory) and -m are passed.
        Process all subdfiles of -d, and deal with conflicts.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(prepare_workdir(tmpdir))
            path = tempdir / 'test' / "dc.json"
            mock_response.return_value = path.read_text()
            mock_poster.return_value = tempdir / 'test' / "poster.png"
            mp4_file = tempdir / 'test' / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4"
            targetfile = tempdir / 'test' / "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p.mp4"
            targetfile2 = tempdir / 'test' / "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.2.1080p.mp4"
            mp4_file.rename(targetfile)
            shutil.copy(targetfile, targetfile2)


            main(['-f',targetfile])
            output = MP4(targetfile.parent / 'DorcelClub - 2021-12-23 - Peeping Tom.mp4')
            self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])

    def test_writing_metadata_from_nfo(self):
        """
        Test renaming and writing a movie's metadata from an nfo file.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(prepare_workdir(tmpdir))
            #nfo_file = tempdir / 'test' / "ea.nfo"
            mp4_file = tempdir / 'test' / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4"
            targetfile = tempdir / 'test' / "ea.mp4"
            mp4_file.rename(targetfile)
            main(['-f',targetfile,"-i"])
            output = MP4(targetfile.parent / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4')
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_writing_metadata_all_dirs_files(self, mock_poster, mock_response):
        """
        Test multiple directories are processed when -d (directory) and -m are passed.
        Process all subdirs of -d.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(prepare_workdir(tmpdir))
            path =  tempdir / 'test' / 'dc.json'
            response1 = path.read_text()
            path2 = tempdir / 'test' / 'ea.json'
            response2 = path2.read_text()
            mock_response.side_effect = [response1, response1, response2, response2]
            (tempdir / 'targetpath').mkdir()
            input_file = tempdir / 'test' / 'Site.22.01.01.painful.pun.XXX.720p.xpost.mp4'
            targetfile1 = ( tempdir / 'targetpath' /
                "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p.mp4")
            input_file.rename(targetfile1)
            targetfile2 = tempdir / 'targetpath' / "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way.mp4"
            shutil.copy(targetfile1, targetfile2)
            shutil.copy(str (tempdir / 'test' / "poster.png" ) , str( targetfile1.parent / (targetfile1.stem+"_poster_in.png" )))
            shutil.copy(str (tempdir / 'test' / "poster.png" ) , str( targetfile2.parent / (targetfile2.stem+"_poster_in.png" )))
            mock_poster.side_effect = [targetfile1.parent / (targetfile1.stem+"_poster_in.png" ),
                targetfile2.parent / (targetfile2.stem+"_poster_in.png" )]
            main(['-d',os.path.dirname(targetfile1),'-m'])
            output = MP4(tempdir / 'targetpath' / 'DorcelClub - 2021-12-23 - Peeping Tom.mp4')
            self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])
            output = MP4(tempdir / 'targetpath'/ 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4')
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])

if __name__ == '__main__':
    unittest.main()
    