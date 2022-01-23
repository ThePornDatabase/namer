from mutagen.mp4 import MP4, MP4Cover
from namer_types import LookedUpFileInfo, NamerConfig
from namer_ffmpeg import getResolution, updateAudioStreamIfNeeded
import os
from xml.sax.saxutils import escape
import logging

logger = logging.getLogger('metadata')

def resolution_to_hdv_setting(resolution: int) -> int:
    if resolution >= 2160:
        return 3
    if resolution >= 1080:
        return 2
    if resolution >= 720:
        return 1
    return 0 

def update_mp4_file(mp4: str, looked_up: LookedUpFileInfo, poster: str, config: NamerConfig):
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
   
    logger.info("Updating audio and tags for: {}".format(mp4))
    success = updateAudioStreamIfNeeded(mp4, config.language)
    if not success:
        logger.info("Could not process audio or copy {}".format(mp4))

    logger.info("Updating atom tags on: {}".format(mp4))
    video = MP4(mp4)
    video["\xa9nam"] = [looked_up.name]
    video["\xa9day"] = [looked_up.date+"T09:00:00Z"]
    if config.enable_metadataapi_genres:
        looked_up
    else:
        video["\xa9gen"] = [config.default_genre]
    video["tven"] = [looked_up.date]
    video["tvnn"] = [looked_up.site]
    video["stik"] = [9] #Movie
    video["hdvd"] = [resolution_to_hdv_setting(getResolution(mp4))]
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
    if poster is not None:
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
    logger.info("Updated atom tags: {}".format(mp4))
