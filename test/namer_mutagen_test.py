"""
Test for namer_mutagen.py
"""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from test.utils import sample_config, validate_mp4_tags

from mutagen.mp4 import MP4

from namer.filenameparser import parse_file_name
from namer.metadataapi import match
from namer.mutagen import resolution_to_hdv_setting, update_mp4_file
from namer.types import LookedUpFileInfo, NamerConfig


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    def test_video_size(self):
        """
        Test resolution.
        """
        self.assertEqual(resolution_to_hdv_setting(2160), 3)
        self.assertEqual(resolution_to_hdv_setting(1080), 2)
        self.assertEqual(resolution_to_hdv_setting(720), 1)
        self.assertEqual(resolution_to_hdv_setting(480), 0)
        self.assertEqual(resolution_to_hdv_setting(320), 0)
        self.assertEqual(resolution_to_hdv_setting(None), 0)

    @mock.patch("namer.metadataapi.__get_response_json_object")
    def test_writing_metadata(self, mock_response):
        """
        verify tag in place functions.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            testdir = Path(__file__).resolve().parent
            mock_response.return_value = (testdir / "dc.json").read_text()
            targetfile = (tempdir / "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p.mp4")
            shutil.copy(testdir / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4", targetfile)
            poster = tempdir / "poster.png"
            shutil.copy(testdir / "poster.png", poster)
            name_parts = parse_file_name(targetfile.name)
            info = match(name_parts, sample_config())
            update_mp4_file(targetfile, info[0].looked_up, poster, NamerConfig())
            output = MP4(targetfile)
            self.assertEqual(output.get("\xa9nam"), ["Peeping Tom"])

    @mock.patch("namer.metadataapi.__get_response_json_object")
    def test_writing_full_metadata(self, mock_response):
        """
        Test writing metadata to an mp4, including tag information, which is only
        available on scene requests to the porndb using uuid to request scene information.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            testdir = Path(__file__).resolve().parent
            response = testdir / "ea.full.json"
            mock_response.return_value = response.read_text()
            targetfile = (tempdir / "EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4")
            shutil.copy(testdir / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4", targetfile)
            poster = tempdir / "poster.png"
            shutil.copy(testdir / "poster.png", poster)
            name_parts = parse_file_name(targetfile.name)
            info = match(name_parts, sample_config())
            update_mp4_file(targetfile, info[0].looked_up, poster, NamerConfig())
            validate_mp4_tags(self, targetfile)

    @mock.patch("namer.metadataapi.__get_response_json_object")
    def test_non_existant_poster(self, mock_response):
        """
        Test writing metadata to an mp4, including tag information, which is only
        available on scene requests to the porndb using uuid to request scene information.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            testdir = Path(__file__).resolve().parent
            response = testdir / "ea.full.json"
            mock_response.return_value = response.read_text()
            targetfile = (tempdir / "EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4")
            shutil.copy(testdir / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4", targetfile)
            poster = None
            name_parts = parse_file_name(targetfile.name)
            info = match(name_parts, sample_config())
            update_mp4_file(targetfile, info[0].looked_up, poster, NamerConfig())
            validate_mp4_tags(self, targetfile)

    @mock.patch("namer.metadataapi.__get_response_json_object")
    def test_non_existant_file(self, mock_response):
        """
        Test writing metadata to an mp4, including tag information, which is only
        available on scene requests to the porndb using uuid to request scene information.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            testdir = Path(__file__).resolve().parent
            response = testdir / "ea.full.json"
            mock_response.return_value = response.read_text()
            targetfile = (tempdir / "test" / "EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4")
            poster = None
            name_parts = parse_file_name(targetfile.name)
            info = match(name_parts, sample_config())
            update_mp4_file(targetfile, info[0].looked_up, poster, NamerConfig())
            self.assertFalse(targetfile.exists())

    def test_empty_infos(self):
        """
        Test writing metadata to an mp4, including tag information, which is only
        available on scene requests to the porndb using uuid to request scene information.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            targetfile = (tempdir / "test" / "EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4")
            targetfile.parent.mkdir(parents=True, exist_ok=True)
            testdir = Path(__file__).resolve().parent
            shutil.copy(testdir / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4", targetfile)
            info = LookedUpFileInfo()
            update_mp4_file(targetfile, info, None, NamerConfig())
            self.assertTrue(targetfile.exists())
            mp4 = MP4(targetfile)
            self.assertEqual(mp4.get("\xa9nam"), [])
            self.assertEqual(mp4.get("\xa9day"), [])
            self.assertEqual(mp4.get("\xa9alb"), [])
            self.assertEqual(mp4.get("tvnn"), [])


if __name__ == "__main__":
    unittest.main()
