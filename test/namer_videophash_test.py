"""
Test namer_videophash.py
"""
import logging
import shutil
import tempfile
import unittest
from pathlib import Path

import imagehash

from namer.videophashstash import StashVideoPerceptualHash
from namer.videophash import VideoPerceptualHash


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """
    __generator = VideoPerceptualHash()
    __stash_generator = StashVideoPerceptualHash()

    def test_get_phash(self):
        """
        Test phash calculation.
        """
        expected_phash = imagehash.hex_to_hash('88982eebd3552d9c')
        expected_oshash = 'ae547a6b1d8488bc'
        expected_duration = 30

        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            shutil.copytree(Path(__file__).resolve().parent, tempdir / "test")
            file = tempdir / "test" / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4"
            res = self.__generator.get_hashes(file)

            self.assertIsNotNone(res)
            if res:
                self.assertEqual(res.phash, expected_phash)
                self.assertEqual(res.oshash, expected_oshash)
                self.assertEqual(res.duration, expected_duration)

    def test_get_stash_phash(self):
        """
        Test phash calculation.
        """
        expected_phash = imagehash.hex_to_hash('88982eebd3552d9c')
        expected_oshash = 'ae547a6b1d8488bc'
        expected_duration = 30

        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            shutil.copytree(Path(__file__).resolve().parent, tempdir / "test")
            file = tempdir / "test" / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4"
            res = self.__stash_generator.get_hashes(file)

            self.assertIsNotNone(res)
            if res:
                self.assertEqual(res.phash, expected_phash)
                self.assertEqual(res.oshash, expected_oshash)
                self.assertEqual(res.duration, expected_duration)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
