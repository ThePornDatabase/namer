"""
Tests namer_ffmpeg
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from namer.ffmpeg import get_audio_stream_for_lang, get_resolution, update_audio_stream_if_needed


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    def test_get_resolution(self):
        """
        Verifies we can resolutions from mp4 files.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            shutil.copytree(Path(__file__).resolve().parent, tempdir / "test")
            file = tempdir / "test" / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4"
            res = get_resolution(file)
            self.assertEqual(res, 240)

    def test_get_audio_stream(self):
        """
        Verifies we can get audio stream language names from files.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            shutil.copytree(Path(__file__).resolve().parent, tempdir / "test")
            file = tempdir / "test" / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4"
            stream_number = get_audio_stream_for_lang(file, "und")
            self.assertEqual(stream_number, -1)
            stream_number = get_audio_stream_for_lang(file, "eng")
            self.assertEqual(stream_number, -1)

    def test_update_audio_stream(self):
        """
        Verifies we can change default audio stream languages for mp4s.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            shutil.copytree(Path(__file__).resolve().parent, tempdir / "test")
            file = tempdir / "test" / "Site.22.01.01.painful.pun.XXX.720p.xpost_wrong.mp4"
            stream_number = get_audio_stream_for_lang(file, "und")
            self.assertEqual(stream_number, -1)
            stream_number = get_audio_stream_for_lang(file, "eng")
            self.assertEqual(stream_number, 1)
            update_audio_stream_if_needed(file, "eng")
            stream_number = get_audio_stream_for_lang(file, "eng")
            self.assertEqual(stream_number, -1)


if __name__ == "__main__":
    unittest.main()
