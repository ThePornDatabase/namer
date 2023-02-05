"""
Test for namer_mutagen.py
"""
import shutil
import tempfile
import unittest
from pathlib import Path
import hashlib

from mutagen.mp4 import MP4

from namer.configuration import NamerConfig
from namer.fileinfo import parse_file_name
from namer.ffmpeg import FFMpeg
from namer.metadataapi import match
from namer.mutagen import resolution_to_hdv_setting, update_mp4_file
from namer.comparison_results import LookedUpFileInfo
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
            name_parts = parse_file_name(target_file.name, config)
            info = match(name_parts, config)
            ffprobe_results = FFMpeg().ffprobe(target_file)
            update_mp4_file(target_file, info.results[0].looked_up, poster, ffprobe_results, NamerConfig())
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
            name_parts = parse_file_name(target_file.name, config)
            info = match(name_parts, config)
            ffprobe_results = FFMpeg().ffprobe(target_file)
            update_mp4_file(target_file, info.results[0].looked_up, poster, ffprobe_results, NamerConfig())
            validate_mp4_tags(self, target_file)

    def test_sha_sum_two_identical_transformations(self):
        """
        Test that adding metadata to two identical files on two different systems, at two different times
        produces the shame bytes (via sha256)
        """
        # when the id = <id>
        expected_on_all_oses = '1772fcba7610818eaef63d3e268c5ea9134b4531680cdb66ae6e16a3a1c20acc'

        sha_1 = None
        sha_2 = None
        with environment() as (tempdir, _parrot, config):
            test_dir = Path(__file__).resolve().parent
            target_file = (tempdir / "EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4")
            shutil.copy(test_dir / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4", target_file)
            poster = tempdir / "poster.png"
            shutil.copy(test_dir / "poster.png", poster)
            name_parts = parse_file_name(target_file.name, config)
            info = match(name_parts, config)
            ffprobe_results = FFMpeg().ffprobe(target_file)
            update_mp4_file(target_file, info.results[0].looked_up, poster, ffprobe_results, NamerConfig())
            validate_mp4_tags(self, target_file)
            sha_1 = hashlib.sha256(target_file.read_bytes()).digest().hex()
        with environment() as (tempdir, _parrot, config):
            test_dir = Path(__file__).resolve().parent
            target_file = (tempdir / "EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4")
            shutil.copy(test_dir / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4", target_file)
            poster = tempdir / "poster.png"
            shutil.copy(test_dir / "poster.png", poster)
            name_parts = parse_file_name(target_file.name, config)
            info = match(name_parts, config)
            ffprobe_results = FFMpeg().ffprobe(target_file)
            update_mp4_file(target_file, info.results[0].looked_up, poster, ffprobe_results, NamerConfig())
            validate_mp4_tags(self, target_file)
            sha_2 = hashlib.sha256(target_file.read_bytes()).digest().hex()
        self.assertEqual(str(sha_1), str(sha_2))
        self.assertEqual(sha_1, expected_on_all_oses)

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
            name_parts = parse_file_name(target_file.name, config)
            info = match(name_parts, config)
            ffprobe_results = FFMpeg().ffprobe(target_file)
            update_mp4_file(target_file, info.results[0].looked_up, poster, ffprobe_results, NamerConfig())
            validate_mp4_tags(self, target_file)

    def test_non_existent_file(self):
        """
        Test writing metadata to an mp4, including tag information, which is only
        available on scene requests to the porndb using uuid to request scene information.
        """
        with environment() as (tempdir, _parrot, config):
            targetfile = (tempdir / "test" / "EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4")
            poster = None
            name_parts = parse_file_name(targetfile.name, config)
            info = match(name_parts, config)
            ffprobe_results = FFMpeg().ffprobe(targetfile)
            update_mp4_file(targetfile, info.results[0].looked_up, poster, ffprobe_results, config)
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
            ffprobe_results = FFMpeg().ffprobe(target_file)
            update_mp4_file(target_file, info, None, ffprobe_results, NamerConfig())
            self.assertTrue(target_file.exists())
            mp4 = MP4(target_file)
            self.assertEqual(mp4.get("\xa9nam"), [])
            self.assertEqual(mp4.get("\xa9day"), [])
            self.assertEqual(mp4.get("\xa9alb"), [])
            self.assertEqual(mp4.get("tvnn"), [])


if __name__ == "__main__":
    unittest.main()
