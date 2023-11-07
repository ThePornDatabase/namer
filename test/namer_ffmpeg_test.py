"""
Tests namer_ffmpeg
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from namer.ffmpeg import FFMpeg


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    def test_get_resolution(self):
        """
        Verifies we can resolutions from mp4 files.
        """
        with tempfile.TemporaryDirectory(prefix='test') as tmpdir:
            tempdir = Path(tmpdir)
            shutil.copytree(Path(__file__).resolve().parent, tempdir / 'test')
            file = tempdir / 'test' / 'Site.22.01.01.painful.pun.XXX.720p.xpost.mp4'
            results = FFMpeg().ffprobe(file)
            self.assertIsNotNone(results)
            if results:
                res = results.get_resolution()
                self.assertEqual(res, 240)

    def test_get_audio_stream(self):
        """
        Verifies we can get audio stream language names from files.
        """
        with tempfile.TemporaryDirectory(prefix='test') as tmpdir:
            tempdir = Path(tmpdir)
            shutil.copytree(Path(__file__).resolve().parent, tempdir / 'test')
            file = tempdir / 'test' / 'Site.22.01.01.painful.pun.XXX.720p.xpost.mp4'
            stream_number = FFMpeg().get_audio_stream_for_lang(file, 'und')
            self.assertEqual(stream_number, -1)
            stream_number = FFMpeg().get_audio_stream_for_lang(file, 'eng')
            self.assertEqual(stream_number, -1)

    def test_ffprobe(self) -> None:
        """
        read stream info.
        """
        with tempfile.TemporaryDirectory(prefix='test') as tmpdir:
            tempdir = Path(tmpdir)
            shutil.copytree(Path(__file__).resolve().parent, tempdir / 'test')
            file = tempdir / 'test' / 'Site.22.01.01.painful.pun.XXX.720p.xpost_wrong.mp4'
            results = FFMpeg().ffprobe(file)
            self.assertIsNotNone(results)
            if results:
                self.assertTrue(results.get_all_streams()[0].is_video())
                self.assertEqual(results.get_all_streams()[0].bit_rate, 8487)
                self.assertEqual(results.get_all_streams()[0].height, 240)
                self.assertEqual(results.get_all_streams()[0].width, 320)
                self.assertEqual(results.get_all_streams()[0].avg_frame_rate, 15.0)
                self.assertEqual(results.get_all_streams()[0].codec_name, 'h264')
                self.assertGreaterEqual(results.get_all_streams()[0].duration, 30)
                self.assertTrue(results.get_all_streams()[1].is_audio())
                self.assertEqual(results.get_all_streams()[1].disposition_default, True)
                self.assertEqual(results.get_all_streams()[1].tags_language, 'und')
                self.assertTrue(results.get_all_streams()[2].is_audio())
                self.assertEqual(results.get_all_streams()[2].disposition_default, False)
                self.assertEqual(results.get_all_streams()[2].tags_language, 'eng')
                self.assertEqual(results.get_default_video_stream(), results.get_all_streams()[0])
                self.assertEqual(results.get_default_audio_stream(), results.get_all_streams()[1])
                self.assertEqual(results.get_audio_stream('eng'), results.get_all_streams()[2])
                self.assertEqual(results.get_audio_stream('und'), results.get_all_streams()[1])

    def test_update_audio_stream(self):
        """
        Verifies we can change default audio stream languages for mp4's.
        """
        with tempfile.TemporaryDirectory(prefix='test') as tmpdir:
            tempdir = Path(tmpdir)
            shutil.copytree(Path(__file__).resolve().parent, tempdir / 'test')
            file = tempdir / 'test' / 'Site.22.01.01.painful.pun.XXX.720p.xpost_wrong.mp4'
            stream_number = FFMpeg().get_audio_stream_for_lang(file, 'und')
            self.assertEqual(stream_number, -1)
            stream_number = FFMpeg().get_audio_stream_for_lang(file, 'eng')
            self.assertEqual(stream_number, 1)
            FFMpeg().update_audio_stream_if_needed(file, 'eng')
            stream_number = FFMpeg().get_audio_stream_for_lang(file, 'eng')
            self.assertEqual(stream_number, -1)

    def test_file_ffmpeg(self):
        versions = FFMpeg().ffmpeg_version()
        for _, version in versions.items():
            self.assertIsNotNone(version)


if __name__ == '__main__':
    unittest.main()
