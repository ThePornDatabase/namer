"""
Test for namer_mutagen.py
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from mutagen.mp4 import MP4

from namer.filenameparser import parse_file_name
from namer.metadataapi import match
from namer.mutagen import resolution_to_hdv_setting, update_mp4_file
from namer.types import LookedUpFileInfo, NamerConfig
from test.utils import validate_mp4_tags
from test.namer_metadataapi_test import environment


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

    def test_writing_metadata(self):
        """
        verify tag in place functions.
        """
        with environment() as (tempdir, _parrot, config):
            test_dir = Path(__file__).resolve().parent
            poster = tempdir / "poster.png"
            shutil.copy(test_dir / "poster.png", poster)
            target_file = (tempdir / "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p.mp4")
            shutil.copy(test_dir / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4", target_file)
            name_parts = parse_file_name(target_file.name)
            info = match(name_parts, config)
            update_mp4_file(target_file, info[0].looked_up, poster, NamerConfig())
            output = MP4(target_file)
            self.assertEqual(output.get("\xa9nam"), ["Peeping Tom"])

    def test_writing_full_metadata(self):
        """
        Test writing metadata to a mp4, including tag information, which is only
        available on scene requests to the porndb using uuid to request scene information.
        """
        with environment() as (tempdir, _parrot, config):
            test_dir = Path(__file__).resolve().parent
            target_file = (tempdir / "EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4")
            shutil.copy(test_dir / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4", target_file)
            poster = tempdir / "poster.png"
            shutil.copy(test_dir / "poster.png", poster)
            name_parts = parse_file_name(target_file.name)
            info = match(name_parts, config)
            update_mp4_file(target_file, info[0].looked_up, poster, NamerConfig())
            validate_mp4_tags(self, target_file)

    def test_non_existent_poster(self):
        """
        Test writing metadata to an mp4, including tag information, which is only
        available on scene requests to the porndb using uuid to request scene information.
        """
        with environment() as (tempdir, _parrot, config):
            test_dir = Path(__file__).resolve().parent
            target_file = (tempdir / "EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4")
            shutil.copy(test_dir / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4", target_file)
            poster = None
            name_parts = parse_file_name(target_file.name)
            info = match(name_parts, config)
            update_mp4_file(target_file, info[0].looked_up, poster, NamerConfig())
            validate_mp4_tags(self, target_file)

    def test_non_existent_file(self):
        """
        Test writing metadata to an mp4, including tag information, which is only
        available on scene requests to the porndb using uuid to request scene information.
        """
        with environment() as (tempdir, _parrot, config):
            targetfile = (tempdir / "test" / "EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4")
            poster = None
            name_parts = parse_file_name(targetfile.name)
            info = match(name_parts, config)
            update_mp4_file(targetfile, info[0].looked_up, poster, config)
            self.assertFalse(targetfile.exists())

    def test_empty_infos(self):
        """
        Test writing metadata to an mp4, including tag information, which is only
        available on scene requests to the porndb using uuid to request scene information.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            target_file = (tempdir / "test" / "EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4")
            target_file.parent.mkdir(parents=True, exist_ok=True)
            test_dir = Path(__file__).resolve().parent
            shutil.copy(test_dir / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4", target_file)
            info = LookedUpFileInfo()
            update_mp4_file(target_file, info, None, NamerConfig())
            self.assertTrue(target_file.exists())
            mp4 = MP4(target_file)
            self.assertEqual(mp4.get("\xa9nam"), [])
            self.assertEqual(mp4.get("\xa9day"), [])
            self.assertEqual(mp4.get("\xa9alb"), [])
            self.assertEqual(mp4.get("tvnn"), [])


if __name__ == "__main__":
    unittest.main()
