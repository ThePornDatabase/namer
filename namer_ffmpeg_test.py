import os
from sys import stdout
from distutils.file_util import copy_file
import unittest
from namer_ffmpeg import getResolution, getAudioStreamForLang

class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    current=os.path.dirname(os.path.abspath(__file__))

    def test_get_resolution(self):
        file = os.path.join(os.path.join(self.current, "test"), "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4")
        res = getResolution(file)
        self.assertEqual(res, 240)

    def test_get_audio_stream(self):
        file = os.path.join(os.path.join(self.current, "test"), "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4")
        id = getAudioStreamForLang(file, "und")
        self.assertEqual(id, None)
        id = getAudioStreamForLang(file, "eng")
        self.assertEqual(id, None)

if __name__ == '__main__':
    unittest.main()        