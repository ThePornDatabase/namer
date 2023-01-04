"""
Updates mp4 files with metadata tags readable by Plex and Apple TV App.
"""

from pathlib import Path
from typing import Any, List, Optional

from loguru import logger
from mutagen.mp4 import MP4, MP4Cover, MP4StreamInfoError

from namer.configuration import NamerConfig
from namer.ffmpeg import FFMpeg, FFProbeResults
from namer.comparison_results import LookedUpFileInfo


def resolution_to_hdv_setting(resolution: Optional[int]) -> int:
    """
    Using the resolution (height) of a video stream return the atom value for hd video
    """
    if not resolution:
        return 0
    elif resolution >= 2160:
        return 3
    elif resolution >= 1080:
        return 2
    elif resolution >= 720:
        return 1

    return 0


def set_single_if_not_none(video: MP4, atom: str, value: Any):
    """
    Set a single atom on the video if it is not None.
    """
    video[atom] = [value] if value is not None else []


def set_array_if_not_none(video: MP4, atom: str, value: List[str]):
    """
    Set an array atom on the video if it is not None.
    """
    video[atom] = value if value is not None else []


def get_mp4_if_possible(mp4: Path, ffmpeg: FFMpeg) -> MP4:
    """
    Attempt to read a mp4 file to prepare for edit.
    """
    try:
        video = MP4(mp4)
    except MP4StreamInfoError:
        ffmpeg.attempt_fix_corrupt(mp4)
        video = MP4(mp4)

    return video


@logger.catch
def update_mp4_file(mp4: Path, looked_up: LookedUpFileInfo, poster: Optional[Path], ffprobe_results: Optional[FFProbeResults], config: NamerConfig):
    # pylint: disable=too-many-statements
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

    logger.info("Updating audio and tags for: {}", mp4)
    success = config.ffmpeg.update_audio_stream_if_needed(mp4, config.language)
    if not success:
        logger.info("Could not process audio or copy {}", mp4)

    logger.info("Updating atom tags on: {}", mp4)
    if mp4 and mp4.exists():
        video: MP4 = get_mp4_if_possible(mp4, config.ffmpeg)
        video.clear()
        set_single_if_not_none(video, "\xa9nam", looked_up.name)
        video["\xa9day"] = [looked_up.date + "T09:00:00Z"] if looked_up.date else []

        if config.enable_metadataapi_genres:
            set_array_if_not_none(video, "\xa9gen", looked_up.tags)
        else:
            set_array_if_not_none(video, "keyw", looked_up.tags)
            set_single_if_not_none(video, "\xa9gen", config.default_genre)

        set_single_if_not_none(video, "tvnn", looked_up.site)
        set_single_if_not_none(video, "\xa9alb", looked_up.site)
        video["stik"] = [9]  # Movie

        if ffprobe_results:
            stream = ffprobe_results.get_default_video_stream()
            if stream:
                resolution = resolution_to_hdv_setting(stream.height)
                set_single_if_not_none(video, "hdvd", resolution)

        set_single_if_not_none(video, "ldes", looked_up.description)
        set_single_if_not_none(video, "\xa9cmt", looked_up.source_url)
        video["----:com.apple.iTunes:iTunEXTC"] = "mpaa|XXX|0|".encode("UTF-8", errors="ignore")
        itunes_movie = '<?xml version="1.0" encoding="UTF-8"?><plist version="1.0"><dict>'
        itunes_movie += f"<key>copy-warning</key><string>{looked_up.source_url}</string>"
        itunes_movie += f"<key>studio</key> <string>{looked_up.site}</string>"
        itunes_movie += f"<key>tpdbid</key> <string>{looked_up.look_up_site_id}</string>"
        itunes_movie += "<key>cast</key> <array>"

        for performer in looked_up.performers:
            if performer.name:
                itunes_movie += f"<dict> <key>name</key> <string>{performer.name}</string>"
                if performer.role:
                    itunes_movie += f"<key>role</key> <string>{performer.role}</string>"
                itunes_movie += "</dict>"

        itunes_movie += "</array>"
        itunes_movie += "<key>codirectors</key> <array></array>"
        itunes_movie += "<key>directors</key> <array></array>"
        itunes_movie += "<key>screenwriters</key><array></array>"
        itunes_movie += "</dict></plist>"
        video["----:com.apple.iTunes:iTunMOVI"] = itunes_movie.encode("UTF-8", errors="ignore")
        add_poster(poster, video)
        video.save()
        logger.info("Updated atom tags: {}", mp4)
    else:
        logger.warning("Can not update tags of a non-existent file: {}", mp4)


def add_poster(poster, video):
    """
    Adds a poster to the mp4 metadata if available and correct format.
    """
    if poster:
        with open(poster, "rb") as file:
            ext = poster.suffix.upper()
            image_format = None
            if ext in [".JPEG", ".JPG"]:
                image_format = MP4Cover.FORMAT_JPEG
            elif ext == ".PNG":
                image_format = MP4Cover.FORMAT_PNG

            if image_format:
                video["covr"] = [MP4Cover(file.read(), image_format)]
