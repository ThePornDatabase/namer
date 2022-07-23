"""
ffmpeg is access through this file, it is used to find the video stream's resolution,
and update audio streams "Default" setting.   Apple video players require there be
only one default audio stream, and this script lets you set it with the correct language
code if there are more than one audio streams and if they are correctly labeled.
See:  https://iso639-3.sil.org/code_tables/639/data/ for language codes.
"""

import json
import shutil
import string
import subprocess
from io import BytesIO
from pathlib import Path
from random import choices
from types import SimpleNamespace
from typing import List, Optional

import ffmpeg
from loguru import logger
from PIL.Image import Image, open

from namer.types import FFProbeFormat, FFProbeResults, FFProbeStream


def get_resolution(file: Path) -> int:
    """
    Gets the vertical resolution of a mp4 file.  For example, 720, 1080, 2160...
    Returns zero if resolution can not be determined.
    """
    logger.info("resolution stream of file {}", file)

    with subprocess.Popen(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=height",
            "-of",
            "csv=p=0",
            file,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    ) as process:
        stdout, stderr = process.communicate()
        success = process.returncode == 0
        output = 0
        if stdout is not None:
            output = stdout
        if not success:
            logger.warning("Error getting resolution of file {}", file)
            if stderr is not None:
                logger.warning(stderr)
        if output is not None:
            logger.info("output {}", output)
            return int(output)
    return 0


def ffprobe(file: Path) -> Optional[FFProbeResults]:
    """
    Get the typed results of probing a video stream with ffprobe.
    """
    logger.info("ffprobe file {}", file)
    ffprobe_out = ffmpeg.probe(file)
    if not ffprobe_out:
        return

    streams = [stream for stream in ffprobe_out['streams'] if stream['codec_type'] in ('video', 'audio')]
    if not streams:
        return

    output: List[FFProbeStream] = []
    for stream in streams:
        ff_stream = FFProbeStream()
        ff_stream.bit_rate = int(stream['bit_rate'])
        ff_stream.codec_name = stream['codec_name']
        ff_stream.codec_type = stream['codec_type']
        ff_stream.index = int(stream['index'])
        ff_stream.duration = float(stream['duration'])

        ff_stream.height = int(stream['height']) if 'height' in stream else -1
        ff_stream.width = int(stream['width']) if 'width' in stream else -1
        ff_stream.tags_language = stream['tags']['language'] if 'tags' in stream else None

        if 'disposition' in stream:
            ff_stream.disposition_attached_pic = stream['disposition']['attached_pic'] == 1
            ff_stream.disposition_default = stream['disposition']['default'] == 1

        if 'avg_frame_rate' in stream:
            numer, denom = stream['avg_frame_rate'].split('/', 2)
            numer, denom = int(numer), int(denom)
            if numer != 0 and denom != 0:
                ff_stream.avg_frame_rate = numer / denom

        output.append(ff_stream)
    
    format = FFProbeFormat()
    if 'format' in ffprobe_out:
        format.bit_rate = int(ffprobe_out['format']['bit_rate'])
        format.duration = float(ffprobe_out['format']['duration'])
        format.size = int(ffprobe_out['format']['size'])
        format.tags = ffprobe_out['format']['tags']

    return FFProbeResults(output, format)


def get_audio_stream_for_lang(mp4_file: Path, language: str) -> int:
    """
    given a mp4 input file and a desired language will return the stream position of that language in the mp4.
    if the language is None, or the stream is not found, or the desired stream is the only default stream, None is returned.
    See: https://iso639-3.sil.org/code_tables/639/data/

    Returns -1 if stream can not be determined
    """

    with subprocess.Popen(
        [
            "ffprobe",
            "-show_streams",
            "-select_streams",
            "a",
            "-of",
            "json",
            "-i",
            mp4_file,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    ) as process:
        stdout, stderr = process.communicate()
        success = process.returncode == 0
        audio_streams_str = None
        if stdout is not None:
            audio_streams_str = stdout
        if not success:
            logger.warning("Error getting audio streams of file {}", mp4_file)
            if stderr is not None:
                logger.warning(stderr)
        logger.info("Target for audio: {}", mp4_file)
        audio_streams = None
        if audio_streams_str is not None:
            audio_streams = json.loads(audio_streams_str, object_hook=lambda d: SimpleNamespace(**d))
        lang_stream = None
        needs_updated = False
        if language:
            test_lang = language.lower()[0:3]
            if audio_streams is not None and hasattr(audio_streams, "streams"):
                for audio_stream in audio_streams.streams:
                    default = audio_stream.disposition.default == 1
                    lang = audio_stream.tags.language
                    if lang == test_lang:
                        lang_stream = audio_stream.index - 1
                        if default is False:
                            needs_updated = True
                    elif default is True:
                        needs_updated = True
                if needs_updated and lang_stream:
                    return lang_stream
    return -1


def update_audio_stream_if_needed(mp4_file: Path, language: Optional[str]) -> bool:
    """
    Returns true if the file had to be edited to have a default audio stream equal to the desired language,
    mostly a concern for apple players (Quicktime/Apple TV/etc.)
    Copies, and potentially updates the default audio stream of a video file.
    """
    random = "".join(choices(population=string.ascii_uppercase + string.digits, k=10))
    work_file = mp4_file.parent / (mp4_file.stem + random + mp4_file.suffix)
    stream = None if language is None else get_audio_stream_for_lang(mp4_file, language)
    if stream is not None and stream >= 0:
        logger.info("Attempt to alter default audio stream of {}", mp4_file)
        with subprocess.Popen(
            [
                "ffmpeg",
                "-i",
                mp4_file,  # input file
                "-map",
                "0",  # copy all stream
                "-disposition:a",
                "none",  # mark all audio streams as not default
                # mark this audio stream as default
                f"-disposition:a:{stream}",
                "default",
                "-c",
                "copy",  # don't re-encode anything.
                work_file,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        ) as process:
            stdout, stderr = process.communicate()
            success = process.returncode == 0
            if not success:
                logger.info("Could not update audio stream for {}", mp4_file)
                if stderr is not None:
                    logger.info(stderr)
            else:
                logger.warning("Return code: {}", process.returncode)
                mp4_file.unlink()
                shutil.move(work_file, mp4_file)
            return success
    return True


def attempt_fix_corrupt(mp4_file: Path) -> bool:
    """
    Attempt to fix corrupt mp4 files.
    """
    random = "".join(choices(population=string.ascii_uppercase + string.digits, k=10))
    work_file = mp4_file.parent / (mp4_file.stem + random + mp4_file.suffix)
    logger.info("Attempt to fix damaged mp4 file: {}", mp4_file)
    with subprocess.Popen(
        [
            "ffmpeg",
            "-i",
            mp4_file,  # input file
            "-c",
            "copy",  # don't re-encode anything.
            work_file,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    ) as process:
        stdout, stderr = process.communicate()
        success = process.returncode == 0
        if not success:
            logger.info("Could not fix mp4 files {}", mp4_file)
            if stderr is not None:
                logger.info(stderr)
        else:
            logger.warning("Return code: {}", process.returncode)
            mp4_file.unlink()
            shutil.move(work_file, mp4_file)
        return success


def extract_screenshot(file: Path, time: float, screenshot_width: int = -1) -> Image:
    out, _ = (
        ffmpeg
        .input(file, ss=time)
        .filter('scale', screenshot_width, -1)
        .output('pipe:', vframes=1, format='apng')
        .run(quiet=True, capture_stdout=True)
    )
    out = BytesIO(out)
    image = open(out)

    return image
