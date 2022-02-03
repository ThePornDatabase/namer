"""
Test for namer_mutagen.py
"""
import unittest
from unittest import mock
import os
from mutagen.mp4 import MP4
from namer_mutagen import update_mp4_file
from namer_metadataapi import match
from namer_metadataapi_test import readfile
from namer_file_parser import parse_file_name
from namer_types import NamerConfig
from namer_dirscanner_test import prepare_workdir

class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    current=os.path.dirname(os.path.abspath(__file__))

    @mock.patch("namer_metadataapi.__get_response_json_object")
    def test_writing_metadata(self, mock_response):
        with prepare_workdir() as tmpdir:
            mock_response.return_value = readfile(os.path.join(tmpdir,"test","DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.json"))
            mp4_file = os.path.join(tmpdir,"test","Site.22.01.01.painful.pun.XXX.720p.xpost.mp4")
            targetfile = os.path.join(tmpdir,"test","DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p.mp4")
            os.rename(mp4_file, targetfile)
            poster = os.path.join(tmpdir,"test","poster.png")
            name_parts = parse_file_name(targetfile)
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
        with prepare_workdir() as tmpdir:
            mock_response.return_value = readfile(os.path.join(tmpdir,"test","full.json"))
            mp4_file = os.path.join(tmpdir,"test","Site.22.01.01.painful.pun.XXX.720p.xpost.mp4")
            targetfile = os.path.join(tmpdir,"test","EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4")
            os.rename(mp4_file, targetfile)
            poster = os.path.join(tmpdir,"test","poster.png")
            name_parts = parse_file_name(targetfile)
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
