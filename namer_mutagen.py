from mutagen.mp4 import MP4, MP4Cover
from namer_types import FileNameParts, LookedUpFileInfo
from namer_metadataapi import metadataapi_response_to_data
from namer_ffmpeg import getResolution, copyAndUpdateAudioStreamIfNeeded
import json
import os
import unittest
import tempfile
from types import SimpleNamespace
from distutils.file_util import copy_file
from distutils.dir_util import copy_tree
from xml.sax.saxutils import escape


def resolution_to_hdv_setting(resolution: int) -> int:
    if resolution >= 2160:
        return 3
    if resolution >= 1080:
        return 2
    if resolution >= 720:
        return 1
    return 0 

def update_mp4_file(looked_up: LookedUpFileInfo, mp4: str , dir: str, poster: str, language: str):
    """
    us-tv|TV-MA|600|
    us-tv|TV-14|500|
    us-tv|TV-PG|400|
    us-tv|TV-G|300|
    us-tv|TV-Y|200|
    us-tv|TV-Y7|100|
    us-tv||0|

    mpaa|UNRATED|600|
    mpaa|NC-17|500|
    mpaa|R|400|
    mpaa|PG-13|300|
    mpaa|PG|200|
    mpaa|G|100|
    mpaa|XXX|0|
    """
    output = os.path.join(dir, looked_up.new_file_name())
    print("Updating audio and moving file to: {}".format(output))
    success = copyAndUpdateAudioStreamIfNeeded(mp4, output, language)
    if not success:
        print("Could not process audio or copy {}".format(mp4))
        output = mp4
    elif not output == mp4:
        os.remove(mp4)
        print("Removed source file {}".format(mp4))

    print("Updating atom tags on: {}".format(output))
    video = MP4(output)
    video["\xa9nam"] = [looked_up.name]
    video["\xa9day"] = [looked_up.date+"T09:00:00Z"]
    video["\xa9gen"] = ["Adult"]
    video["tven"] = [looked_up.date]
    video["tvnn"] = [looked_up.site]
    video["stik"] = [9] #Movie
    video["hdvd"] = [resolution_to_hdv_setting(getResolution(output))]
    video["ldes"] = [looked_up.description]
    video["----:com.apple.iTunes:iTunEXTC"] = 'mpaa|XXX|0|'.encode("UTF-8", errors="ignore")
#    video["catg"] = looked_up.  #categories
#    video["keyw"] = looked_up.  #keywords
    

    iTunMOVI = '<?xml version="1.0" encoding="UTF-8"?><plist version="1.0"><dict>'
    iTunMOVI += '<key>copy-warning</key><string>{}</string>'.format(escape(looked_up.source_url))
    iTunMOVI += '<key>studio</key> <string>{}</string>'.format(escape(looked_up.site))
    iTunMOVI += '<key>tpdbid</key> <string>{}</string>'.format(looked_up.look_up_site_id)
    iTunMOVI += '<key>cast</key> <array>'
    for performer in looked_up.performers:
        if performer.name:
            iTunMOVI += '<dict> <key>name</key> <string>{}</string>'.format(escape(performer.name))
            if performer.role:
                iTunMOVI += '<key>role</key> <string>{}</string>'.format(escape(performer.role))
            iTunMOVI += '</dict>'
    iTunMOVI += '</array>'
    iTunMOVI += '<key>codirectors</key> <array></array>'
    iTunMOVI += '<key>directors</key> <array></array>'
    iTunMOVI += '<key>screenwriters</key><array></array>'
    iTunMOVI += '</dict></plist>'
    video["----:com.apple.iTunes:iTunMOVI"] = iTunMOVI.encode("UTF-8", errors="ignore")
    with open(poster, "rb") as f:
        ext = os.path.splitext(poster)[1].upper()
        imageformat = None
        if ext in ['.JPEG', '.JPG']:
            imageformat=MP4Cover.FORMAT_JPEG
        elif ext == '.PNG':
            imageformat=MP4Cover.FORMAT_PNG
        if imageformat:
            video["covr"] = [
                MP4Cover(f.read(), imageformat)
            ]
    video.save()
    print("Updated atom tags: {}".format(output))    
    

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


    def test_find_largest_file_in_glob(self):
        tmpdir = UnitTestAsTheDefaultExecution.prepare_workdir()
        targetfile = os.path.join(tmpdir.name, "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4")
        poster = os.path.join(tmpdir.name, "poster.png")
        with open(os.path.join(self.current,"test","DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.json"),'r') as days_file:
            json_object = json.loads(days_file.read(), object_hook=lambda d: SimpleNamespace(**d))
            name_parts = FileNameParts()
            name_parts.date = "2021-12-23"
            name_parts.site = "DorcelClub"
            name_parts.extension = ".mp4"
            info = metadataapi_response_to_data(json_object, "url", "", name_parts)
            #video = MP4(targetfile)
            update_mp4_file(info[0], targetfile, '/tmp', poster, 'eng')
            tmpdir.cleanup()

if __name__ == '__main__':
    unittest.main()        