"""
Test namer_videophash.py
"""
import logging
import shutil
import tempfile
import unittest
from pathlib import Path

import imagehash
import pytest

from namer.videophash import VideoPerceptualHash


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """
    __tools_path: Path = Path(__file__).resolve().parent.parent / 'tools'
    __stash_path: Path = __tools_path / 'stash_phash'
    __generator = VideoPerceptualHash(__stash_path)

    def test_get_phash(self):
        """
        Test phash calculation.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            shutil.copytree(Path(__file__).resolve().parent, tempdir / "test")
            file = tempdir / "test" / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4"
            res = self.__generator.get_phash(file)

        expected_hash = imagehash.hex_to_hash('88982eebd3552d9c')
        self.assertEqual(res, expected_hash)

    @pytest.mark.skip(reason="need to grab stash_phash tool")
    def test_get_stash_phash(self):
        """
        Test phash calculation.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            shutil.copytree(Path(__file__).resolve().parent, tempdir / "test")
            file = tempdir / "test" / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4"
            res = self.__generator.get_stash_phash(file)

        expected_hash = imagehash.hex_to_hash('88982eebd3552d9c')
        self.assertEqual(res, expected_hash)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
