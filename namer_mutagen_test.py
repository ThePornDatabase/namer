"""
Test for namer_mutagen.py
"""
from pathlib import Path
import unittest
from unittest import mock
import os
import tempfile
import shutil
from mutagen.mp4 import MP4
from namer_mutagen import update_mp4_file
from namer_metadataapi import match
from namer_file_parser import parse_file_name
from namer_types import NamerConfig
from namer_dirscanner_test import prepare_workdir

class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    @mock.patch("namer_metadataapi.__get_response_json_object")
    def test_writing_metadata(self, mock_response):
        """
        verify tag in place functions.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(prepare_workdir(tmpdir))
            message = tempdir / "test" / "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.json"
            mock_response.return_value = message.read_text()
            mp4_file = tempdir / "test" / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4"
            targetfile = tempdir / "test" / "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p.mp4"
            shutil.move(mp4_file, targetfile)
            poster = tempdir / "test" / "poster.png"
            name_parts = parse_file_name(targetfile.name)
            info = match(name_parts, "")
            update_mp4_file(targetfile, info[0].looked_up, poster, NamerConfig())
            output = MP4(targetfile)
            self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])


    @mock.patch("namer_metadataapi.__get_response_json_object")
    def test_writing_full_metadata(self, mock_response):
        """
        Test writing metadata to an mp4, including tag information, which is only
        available on scene requests to the porndb using uuid to request scene information.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(prepare_workdir(tmpdir))
            response = tempdir / "test" / "full.json"
            mock_response.return_value = response.read_text()
            mp4_file = tempdir / "test" / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4"
            targetfile = tempdir / "test" / "EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4"
            shutil.move(mp4_file, targetfile)
            poster = tempdir / "test" / "poster.png"
            name_parts = parse_file_name(targetfile.name)
            info = match(name_parts, "")
            update_mp4_file(targetfile, info[0].looked_up, poster, NamerConfig())
            output = MP4(targetfile)
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])
            self.assertEqual(['Anal', 'Ass', 'Ass to mouth', 'Big Dick', 'Blowjob', 'Blowjob - Double', 'Brunette', 'Bubble Butt',
                              'Cum swallow', 'Deepthroat', 'FaceSitting', 'Facial', 'Gonzo / No Story', 'HD Porn', 'Hairy Pussy',
                              'Handjob', 'Hardcore', 'Latina', 'MILF', 'Pussy to mouth', 'Rimming', 'Sex', 'Tattoo', 'Threesome',
                              'Toys / Dildos'], output.get('keyw'))


if __name__ == '__main__':
    unittest.main()
