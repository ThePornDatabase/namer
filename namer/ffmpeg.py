"""
ffmpeg is access through this file, it is used to find the video streams resolution,
and update audio streams "Default" setting.   Apple video players require there be
only one default audio stream, and this script lets you set it with the correct language
code their are more than one audio streams and if they are correctly labeled.
See:  https://iso639-3.sil.org/code_tables/639/data/
"""

import json
import shutil
from types import SimpleNamespace
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
import logging

logger = logging.getLogger('ffmpeg')


def get_resolution(file: str) -> int:
    """
    Gets the vertical resolution of an mp4 file.  For example, 720, 1080, 2160...
    """
    logger.info("resolution stream of file %s", file)

    with subprocess.Popen(['ffprobe',
                           '-v',
                           'error',
                           '-select_streams',
                           'v:0',
                           '-show_entries',
                           'stream=height',
                           '-of',
                           'csv=p=0',
                           file],
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          universal_newlines=True) as process:
        success = process.wait() == 0
        output = process.stdout.read()
        if not success:
            logger.warning("Error gettng resolution of file %s", file)
            logger.warning(process.stderr.read())
        process.stdout.close()
        process.stderr.close()
        logger.info("output %s", output)
        return int(output)
    return None


def get_audio_stream_for_lang(mp4_file: str, language: str) -> int:
    """
    given an mp4 input file and a desired language will return the stream position of that language in the mp4.
    if the language is None, or the stream is not found, or the desired stream is the only default stream, None is returned.
    See: https://iso639-3.sil.org/code_tables/639/data/
    """

    with subprocess.Popen(['ffprobe',
                           '-show_streams',
                           '-select_streams',
                           'a',
                           '-of',
                           'json',
                           '-i',
                           mp4_file],
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          universal_newlines=True) as process:
        success = process.wait() == 0
        audio_streams_str = process.stdout.read()
        if not success:
            logger.warning("Error gettng audio streams of file %s", mp4_file)
            logger.warning(process.stderr.read())
        process.stdout.close()
        process.stderr.close()

        logger.info("Target for audio: %s", mp4_file)

        audio_streams = json.loads(
            audio_streams_str, object_hook=lambda d: SimpleNamespace(**d))
        lang_stream = None
        needs_updated = False
        if language:
            test_lang = language.lower()[0:3]
            if audio_streams is not None and hasattr(audio_streams, 'streams'):
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
    return None


def update_audio_stream_if_needed(mp4_file: Path, language: str) -> bool:
    """
    Returns true if the file had to be edited to have a default audio stream equal to the desired language,
    mostly a concern for apple players (Quicktime/Apple TV/etc.)
    Copies, and potentially updates the default audio stream of a video file.
    """

    with TemporaryDirectory() as tempdir:
        workfile = Path(tempdir) / mp4_file.name
        stream = get_audio_stream_for_lang(mp4_file, language)
        if stream is not None:
            logger.info(
                "Attempt to alter default audio stream of %s", mp4_file)
            with subprocess.Popen(['ffmpeg',
                                   '-i',
                                   mp4_file,  # input file
                                   '-map',
                                   '0',  # copy all stream
                                   '-disposition:a',
                                   'none',  # mark all audio streams as not default
                                   # mark this audio stream as default
                                   f'-disposition:a:{stream}',
                                   'default',
                                   '-c',
                                   'copy',  # don't reencode anything.
                                   workfile],
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.PIPE,
                                  universal_newlines=True) as process:
                stderr = process.stderr.read()
                success = process.wait() == 0
                process.stderr.close()
                if not success:
                    logger.info(
                        "Could not update audio stream for %s", mp4_file)
                    logger.info(stderr)
                else:
                    logger.warning("Return code: %s", process.returncode)
                    mp4_file.unlink()
                    shutil.move(workfile, mp4_file)
                return success
    return True
