"""
Updates mp4 files with metadata tags readable by Plex and Apple TV App.
"""
import os
import logging
from pathlib import Path
from mutagen.mp4 import MP4, MP4Cover
from namer_types import LookedUpFileInfo, NamerConfig
from namer_ffmpeg import get_resolution, update_audio_stream_if_needed

logger = logging.getLogger('metadata')

def resolution_to_hdv_setting(resolution: int) -> int:
    """
    Using the resolution (height) of an video stream return the atom value for hdvideo
    """
    if resolution >= 2160:
        return 3
    if resolution >= 1080:
        return 2
    if resolution >= 720:
        return 1
    return 0

def update_mp4_file(mp4: Path, looked_up: LookedUpFileInfo, poster: str, config: NamerConfig):
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

    logger.info("Updating audio and tags for: %s",mp4)
    success = update_audio_stream_if_needed(mp4, config.language)
    if not success:
        logger.info("Could not process audio or copy %s",mp4)

    logger.info("Updating atom tags on: %s",mp4)
    video = MP4(mp4)
    video["\xa9nam"] = [looked_up.name]
    video["\xa9day"] = [looked_up.date+"T09:00:00Z"]
    if config.enable_metadataapi_genres:
        video["\xa9gen"] = looked_up.tags
    else:
        video["keyw"] = looked_up.tags
        video["\xa9gen"] = [config.default_genre]
    video["tven"] = [looked_up.date]
    video["tvnn"] = [looked_up.site]
    video["stik"] = [9] #Movie
    video["hdvd"] = [resolution_to_hdv_setting(get_resolution(mp4))]
    video["ldes"] = [looked_up.description]
    video["----:com.apple.iTunes:iTunEXTC"] = 'mpaa|XXX|0|'.encode("UTF-8", errors="ignore")
    video["\xa9alb"] = [looked_up.site]

    itunes_movie = '<?xml version="1.0" encoding="UTF-8"?><plist version="1.0"><dict>'
    itunes_movie += f'<key>copy-warning</key><string>{looked_up.source_url}</string>'
    itunes_movie += f'<key>studio</key> <string>{looked_up.site}</string>'
    itunes_movie += f'<key>tpdbid</key> <string>{looked_up.look_up_site_id}</string>'
    itunes_movie += '<key>cast</key> <array>'
    for performer in looked_up.performers:
        if performer.name:
            itunes_movie += f'<dict> <key>name</key> <string>{performer.name}</string>'
            if performer.role:
                itunes_movie += f'<key>role</key> <string>{performer.role}</string>'
            itunes_movie += '</dict>'
    itunes_movie += '</array>'
    itunes_movie += '<key>codirectors</key> <array></array>'
    itunes_movie += '<key>directors</key> <array></array>'
    itunes_movie += '<key>screenwriters</key><array></array>'
    itunes_movie += '</dict></plist>'
    video["----:com.apple.iTunes:iTunMOVI"] = itunes_movie.encode("UTF-8", errors="ignore")

    if poster is not None:
        with open(poster, "rb") as file:
            ext = os.path.splitext(poster)[1].upper()
            imageformat = None
            if ext in ['.JPEG', '.JPG']:
                imageformat=MP4Cover.FORMAT_JPEG
            elif ext == '.PNG':
                imageformat=MP4Cover.FORMAT_PNG
            if imageformat:
                video["covr"] = [
                    MP4Cover(file.read(), imageformat)
                ]
    video.save()
    logger.info("Updated atom tags: %s", mp4)
