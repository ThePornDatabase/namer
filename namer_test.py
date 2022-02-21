"""
Fully test namer.py
"""
from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import List
import unittest
from unittest.mock import patch
import os
import tempfile
from mutagen.mp4 import MP4
from namer import main

ROOT_DIR = './test/'

@dataclass(init=True, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class ProcessingTarget:
    """
    Test data.
    """
    file: Path
    json_search: str
    json_exact: str
    poster: Path
    expect_match: bool

def new_ea(targetdir: Path, use_dir: bool = True, post_stem: str = "", match: bool = True):
    """
    Creates a test mp4 in a temp directory, with a name to match the returned contents of ./test/ea.json
    optionally, names the dir and not the mp4 file to match.
    optionally, inserts a string between the file stem and suffix.
    optionally, will ensure a match doesn't occure.
    """
    current = Path(__file__).resolve().parent
    test_mp4 = current / 'test' / 'Site.22.01.01.painful.pun.XXX.720p.xpost.mp4'
    search_json_file = current / 'test' / 'ea.json'
    exact_json_file = current / 'test' / 'ea.full.json'
    test_poster = current / 'test' / 'poster.png'
    name = 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!' + post_stem
    target_file =  targetdir / (name+'.mp4')
    if use_dir is True:
        target_file = targetdir / name / 'qwerty.mp4'
    os.makedirs(target_file.parent, exist_ok=True)
    shutil.copy(test_mp4, target_file)
    poster = Path(tempfile.mktemp(suffix=".png"))
    shutil.copy(test_poster, poster)
    return ProcessingTarget(target_file, search_json_file.read_text(), exact_json_file.read_text(), poster, match)

def prepare(targets: List[ProcessingTarget], mock_poster, mock_response):
    """
    Prepares mocks for responses based on targets input.
    """
    targets.sort(key= lambda x: str(x.file))
    posters = []
    responses = []
    for target in targets:
        posters.append(target.poster)
        if target.expect_match is True:
            responses.append(target.json_search)
            responses.append(target.json_exact)
        else:
            responses.append('{}')
            responses.append('{}')
    mock_poster.side_effect = posters
    mock_response.side_effect = responses

class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_writing_metadata_file(self, mock_poster, mock_response):
        """
        test namer main method renames and tags in place when -f (video file) is passed
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            targets = [new_ea(tempdir, use_dir=False)]
            prepare(targets, mock_poster, mock_response)
            main(['-f',str(targets[0].file)])
            output = MP4(targets[0].file.parent / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4')
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_writing_metadata_dir(self, mock_poster, mock_response):
        """
        test namer main method renames and tags in place when -d (directory) is passed
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            targets = [new_ea(tempdir, use_dir=True)]
            prepare(targets, mock_poster, mock_response)
            main(['-d',str(targets[0].file.parent)])
            output = MP4(targets[0].file.parent / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4')
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_writing_metadata_all_dirs(self, mock_poster, mock_response):
        """
        Test multiple directories are processed when -d (directory) and -m are passed.
        Process all subdirs of -d.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            targets = [new_ea(tempdir, use_dir=True, post_stem='1'),
                    new_ea(tempdir, use_dir=True, post_stem='2')]
            prepare(targets, mock_poster, mock_response)
            main(['-d',str(targets[0].file.parent.parent), '-m'])
            output = MP4(targets[0].file.parent / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4')
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])
            output = MP4(targets[1].file.parent / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4')
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_writing_metadata_conflict_files(self, mock_poster, mock_response):
        """
        Test multiple files are processed when -d (directory) and -m are passed.
        Process all subdfiles of -d, and deal with conflicts.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            shutil.copytree(Path(__file__).resolve().parent / "test" , tempdir / "test")
            path = tempdir / 'test' / "dc.json"
            mock_response.return_value = path.read_text()
            mock_poster.return_value = tempdir / 'test' / "poster.png"
            mp4_file = tempdir / 'test' / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4"
            targetfile = tempdir / 'test' / "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p.mp4"
            targetfile2 = tempdir / 'test' / "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.2.1080p.mp4"
            mp4_file.rename(targetfile)
            shutil.copy(targetfile, targetfile2)


            main(['-f',str(targetfile)])
            output = MP4(targetfile.parent / 'DorcelClub - 2021-12-23 - Peeping Tom.mp4')
            self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])

    def test_writing_metadata_from_nfo(self):
        """
        Test renaming and writing a movie's metadata from an nfo file.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            current = Path(__file__).resolve().parent
            tempdir = Path(tmpdir)
            nfo_file = current / 'test' / "ea.nfo"
            mp4_file = current / 'test' / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4"
            poster_file =  current / 'test' / "poster.png"
            target_nfo_file = tempdir / "ea.nfo"
            target_mp4_file = tempdir / "ea.mp4"
            target_poster_file = tempdir / "poster.png"
            shutil.copy(mp4_file, target_mp4_file)
            shutil.copy(nfo_file, target_nfo_file)
            shutil.copy(poster_file, target_poster_file)

            main(['-f',str(target_mp4_file),"-i"])
            output = MP4(target_mp4_file.parent / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4')
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_writing_metadata_all_dirs_files(self, mock_poster, mock_response):
        """
        Test multiple directories are processed when -d (directory) and -m are passed.
        Process all subdirs of -d.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            targets = [new_ea(tempdir, use_dir=False, post_stem='1'),
                    new_ea(tempdir, use_dir=False, post_stem='2')]
            prepare(targets, mock_poster, mock_response)
            main(['-d',str(targets[0].file.parent), '-m'])
            output1 = MP4(targets[0].file.parent / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4')
            self.assertEqual(output1.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])
            output2 = MP4(targets[1].file.parent / 'EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!(1).mp4')
            self.assertEqual(output2.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])
            self.assertEqual(output2.get('\xa9day'), ['2022-01-03T09:00:00Z'])
            self.assertEqual(output2.get('\xa9alb'), ['Evil Angel']) # plex collection
            self.assertEqual(output2.get('tvnn'), ['Evil Angel'])
            self.assertEqual(output2.get("\xa9gen"), ['Adult'])
            self.assertEqual(['Anal', 'Ass', 'Ass to mouth', 'Big Dick', 'Blowjob', 'Blowjob - Double', 'Brunette', 'Bubble Butt',
                              'Cum swallow', 'Deepthroat', 'FaceSitting', 'Facial', 'Gonzo / No Story', 'HD Porn', 'Hairy Pussy',
                              'Handjob', 'Hardcore', 'Latina', 'MILF', 'Pussy to mouth', 'Rimming', 'Sex', 'Tattoo', 'Threesome',
                              'Toys / Dildos'], output2.get('keyw'))

if __name__ == '__main__':
    unittest.main()
    