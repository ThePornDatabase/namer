import unittest
from unittest import mock
import os
import tempfile
from distutils.dir_util import copy_tree
from namer_mutagen import update_mp4_file 
from namer_metadataapi import match
from namer_metadataapi_test import readfile
from namer_file_parser import parse_file_name
from mutagen.mp4 import MP4

from namer_types import NamerConfig

class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    current=os.path.dirname(os.path.abspath(__file__))

    def prepare_workdir():
        current=os.path.dirname(os.path.abspath(__file__))
        test_fixture="test"
        tmpdir = tempfile.TemporaryDirectory()
        test_root = os.path.join(tmpdir.name,test_fixture)
        copy_tree(os.path.join(current, test_fixture), tmpdir.name)
        return tmpdir


    @mock.patch("namer_metadataapi.__get_response_json_object")
    def test_writing_metadata(self, mock_response):
        tmpdir = UnitTestAsTheDefaultExecution.prepare_workdir()
        mock_response.return_value = readfile(os.path.join(tmpdir.name,"DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.json"))
        input = os.path.join(tmpdir.name, "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4")
        targetfile = os.path.join(tmpdir.name, "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p.mp4")
        os.rename(input, targetfile)
        poster = os.path.join(tmpdir.name, "poster.png")
        name_parts = parse_file_name(targetfile)
        info = match(name_parts, "")
        update_mp4_file(targetfile, info[0].looked_up, poster, NamerConfig())
        output = MP4(targetfile)
        self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])
        tmpdir.cleanup()



    @mock.patch("namer_metadataapi.__get_response_json_object")
    def test_writing_metadata(self, mock_response):
        tmpdir = UnitTestAsTheDefaultExecution.prepare_workdir()
        mock_response.return_value = readfile(os.path.join(tmpdir.name,"full.json"))
        input = os.path.join(tmpdir.name, "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4")
        targetfile = os.path.join(tmpdir.name, "EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4")
        os.rename(input, targetfile)
        poster = os.path.join(tmpdir.name, "poster.png")
        name_parts = parse_file_name(targetfile)
        info = match(name_parts, "")
        update_mp4_file(targetfile, info[0].looked_up, poster, NamerConfig())
        output = MP4(targetfile)
        self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])
        self.assertEqual(['Anal', 'Ass', 'Ass to mouth', 'Big Dick', 'Blowjob', 'Blowjob - Double', 'Brunette', 'Bubble Butt', 'Cum swallow', 'Deepthroat', 'FaceSitting', 'Facial', 'Gonzo / No Story', 'HD Porn', 'Hairy Pussy', 'Handjob', 'Hardcore', 'Latina', 'MILF', 'Pussy to mouth', 'Rimming', 'Sex', 'Tattoo', 'Threesome', 'Toys / Dildos'], output.get('catg'))
        tmpdir.cleanup()


if __name__ == '__main__':
    unittest.main()      