"""
ffmpeg is access through this file, it is used to find the video stream's resolution,
and update audio streams "Default" setting.   Apple video players require there be
only one default audio stream, and this script lets you set it with the correct language
code if there are more than one audio streams and if they are correctly labeled.
See:  https://iso639-3.sil.org/code_tables/639/data/ for language codes.
"""
import json
import subprocess
from dataclasses import dataclass
import shutil
import string
import re
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from random import choices
from typing import Any, Dict, List, Optional

import ffmpeg
from loguru import logger
from PIL import Image
from pathvalidate import ValidationError

from namer.videophashstash import StashVideoPerceptualHash


@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class FFProbeStream:
    index: int                      # stream number
    codec_name: str                 # "mp3", "h264", "hvec", "png"
    codec_type: str                 # "audio" or "video"
    disposition_default: bool       # default stream of this type
    disposition_attached_pic: bool  # is the "video" stream an attached picture.
    duration: float                 # seconds
    bit_rate: int                   # bitrate of the track
    # audio
    tags_language: Optional[str]            # 3 letters representing language of track (only matters for audio)
    # video only
    width: Optional[int] = None
    height: Optional[int] = None            # 720 1080 2160
    avg_frame_rate: Optional[float] = None  # average frames per second

    def __str__(self) -> str:
        data = self.to_dict()

        return json.dumps(data, indent=2)

    def to_dict(self) -> dict:
        data = {
            'codec_name': self.codec_name,
            'width': self.width,
            'height': self.height,
            'codec_type': self.codec_type,
            'framerate': self.avg_frame_rate,
            'duration': self.duration,
            'disposition_default': self.disposition_default,
        }

        return data

    def is_audio(self) -> bool:
        return self.codec_type == "audio"

    def is_video(self) -> bool:
        return self.codec_type == "video" and (not self.disposition_attached_pic or self.disposition_attached_pic is False)


@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class FFProbeFormat:
    duration: float
    size: int
    bit_rate: int
    tags: Dict[str, str]


@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class FFProbeResults:
    __results: List[FFProbeStream]
    __format: FFProbeFormat

    def __init__(self, data: List[FFProbeStream], probe_format: FFProbeFormat):
        self.__results = data
        self.__format = probe_format

    def get_default_video_stream(self) -> Optional[FFProbeStream]:
        for result in self.__results:
            if result.is_video() and result.disposition_default:
                return result

    def get_default_audio_stream(self) -> Optional[FFProbeStream]:
        for result in self.__results:
            if result.is_audio() and result.disposition_default:
                return result

    def get_audio_stream(self, language_code: str) -> Optional[FFProbeStream]:
        for result in self.__results:
            if result.is_audio() and result.tags_language == language_code:
                return result

    def get_all_streams(self) -> List[FFProbeStream]:
        return self.__results

    def get_format(self) -> FFProbeFormat:
        return self.__format

    def get_resolution(self) -> Optional[int]:
        stream = self.get_default_video_stream()
        if stream:
            return stream.height if stream.height else 0


class FFMpeg:
    __local_dir: Optional[Path] = None
    __ffmpeg_cmd: str = 'ffmpeg'
    __ffprobe_cmd: str = 'ffprobe'

    def __init__(self):
        versions = self.__ffmpeg_version(None)
        if not versions['ffmpeg'] or not versions['ffprobe']:
            home_path: Path = Path(__file__).parent
            phash_path: Path = home_path / 'tools'
            if not phash_path.is_dir():
                phash_path.mkdir(exist_ok=True, parents=True)
            self.__local_dir = phash_path
            versions = self.__ffmpeg_version(phash_path)
            if not versions['ffmpeg'] and not versions['ffprobe']:
                StashVideoPerceptualHash().install_ffmpeg()
            versions = self.__ffmpeg_version(phash_path)
            if not versions['ffmpeg'] and not versions['ffprobe']:
                raise ValidationError(f"could not find ffmpeg/ffprobe on path, or in tools dir: {self.__local_dir}")
            self.__ffmpeg_cmd = str(phash_path / 'ffmpeg')
            self.__ffprobe_cmd = str(phash_path / 'ffprobe')

    @logger.catch
    def ffprobe(self, file: Path) -> Optional[FFProbeResults]:
        """
        Get the typed results of probing a video stream with ffprobe.
        """
        stat = file.stat()
        return self._ffprobe(file, stat.st_size, stat.st_mtime)

    @lru_cache(maxsize=1024)
    def _ffprobe(self, file: Path, file_size: int, file_update: float) -> Optional[FFProbeResults]:
        """
        Get the typed results of probing a video stream with ffprobe.
        """

        logger.info(f'ffprobe file "{file}"')
        ffprobe_out: Optional[Any] = None
        try:
            ffprobe_out = ffmpeg.probe(file, self.__ffprobe_cmd)
        except:
            pass

        if not ffprobe_out:
            return

        streams = [stream for stream in ffprobe_out['streams'] if stream['codec_type'] in ('video', 'audio')]
        if not streams:
            return

        output: List[FFProbeStream] = []
        for stream in streams:
            ff_stream = FFProbeStream()
            ff_stream.bit_rate = int(stream['bit_rate']) if 'bit_rate' in stream else -1
            ff_stream.codec_name = stream['codec_name']
            ff_stream.codec_type = stream['codec_type']
            ff_stream.index = int(stream['index'])
            ff_stream.duration = float(stream['duration']) if 'duration' in stream else -1

            ff_stream.height = int(stream['height']) if 'height' in stream else -1
            ff_stream.width = int(stream['width']) if 'width' in stream else -1
            ff_stream.tags_language = stream['tags']['language'] if 'tags' in stream and 'language' in stream['tags'] else None

            if 'disposition' in stream:
                ff_stream.disposition_attached_pic = stream['disposition']['attached_pic'] == 1
                ff_stream.disposition_default = stream['disposition']['default'] == 1

            if 'avg_frame_rate' in stream:
                numer, denom = stream['avg_frame_rate'].split('/', 2)
                numer, denom = int(numer), int(denom)
                if numer != 0 and denom != 0:
                    ff_stream.avg_frame_rate = numer / denom

            output.append(ff_stream)

        probe_format = FFProbeFormat()
        if 'format' in ffprobe_out:
            probe_format.bit_rate = int(ffprobe_out['format']['bit_rate'])
            probe_format.duration = float(ffprobe_out['format']['duration'])
            probe_format.size = int(ffprobe_out['format']['size'])
            probe_format.tags = ffprobe_out['format']['tags'] if 'tags' in ffprobe_out['format'] else {}

        return FFProbeResults(output, probe_format)

    def get_audio_stream_for_lang(self, file: Path, language: str) -> int:
        """
        given a mp4 input file and a desired language will return the stream position of that language in the mp4.
        if the language is None, or the stream is not found, or the desired stream is the only default stream, None is returned.
        See: https://iso639-3.sil.org/code_tables/639/data/

        Returns -1 if stream can not be determined
        """

        stream_index = -1
        probe = self.ffprobe(file)
        if probe:
            stream = probe.get_audio_stream(language)
            if stream:
                stream_index = stream.index - 1 if not stream.disposition_default else -1

        return stream_index

    def update_audio_stream_if_needed(self, mp4_file: Path, language: Optional[str]) -> bool:
        """
        Returns true if the file had to be edited to have a default audio stream equal to the desired language,
        mostly a concern for apple players (Quicktime/Apple TV/etc.)
        Copies, and potentially updates the default audio stream of a video file.
        """

        random = "".join(choices(population=string.ascii_uppercase + string.digits, k=10))
        temp_filename = f'{mp4_file.stem}_{random}' + mp4_file.suffix
        work_file = mp4_file.parent / temp_filename

        stream = self.get_audio_stream_for_lang(mp4_file, language) if language else None
        if stream and stream >= 0:
            process = (
                ffmpeg
                .input(mp4_file)
                .output(str(work_file), **{
                    'map': 0,  # copy all stream
                    'disposition:a': 'none',  # mark all audio streams as not default
                    f'disposition:a:{stream}': 'default',  # mark this audio stream as default
                    'c': 'copy'  # don't re-encode anything.
                })
                .run_async(quiet=True, cmd=self.__ffmpeg_cmd)
            )

            stdout, stderr = process.communicate()
            stdout, stderr = (stdout.decode('UTF-8') if isinstance(stdout, bytes) else stdout), (stderr.decode('UTF-8') if isinstance(stderr, bytes) else stderr)
            success = process.returncode == 0
            if not success:
                logger.warning("Could not update audio stream for {}", mp4_file)
                if stderr:
                    logger.error(stderr)
            else:
                logger.warning("Return code: {}", process.returncode)
                mp4_file.unlink()
                shutil.move(work_file, mp4_file)

            return success

        return True

    def attempt_fix_corrupt(self, mp4_file: Path) -> bool:
        """
        Attempt to fix corrupt mp4 files.
        """
        random = "".join(choices(population=string.ascii_uppercase + string.digits, k=10))
        temp_filename = f'{mp4_file.stem}_{random}' + mp4_file.suffix
        work_file = mp4_file.parent / temp_filename

        logger.info("Attempt to fix damaged mp4 file: {}", mp4_file)
        process = (
            ffmpeg
            .input(mp4_file)
            .output(str(work_file), c='copy')
            .run_async(quiet=True, cmd=self.__ffmpeg_cmd)
        )

        stdout, stderr = process.communicate()
        stdout, stderr = (stdout.decode('UTF-8') if isinstance(stdout, bytes) else stdout), (stderr.decode('UTF-8') if isinstance(stderr, bytes) else stderr)
        success = process.returncode == 0
        if not success:
            logger.warning("Could not fix mp4 files {}", mp4_file)
            if stderr:
                logger.error(stderr)
        else:
            logger.warning("Return code: {}", process.returncode)
            mp4_file.unlink()
            shutil.move(work_file, mp4_file)

        return success

    def extract_screenshot(self, file: Path, time: float, screenshot_width: int = -1) -> Image.Image:
        out, _ = (
            ffmpeg
            .input(file, ss=time)
            .filter('scale', screenshot_width, -2)
            .output('pipe:', vframes=1, format='apng')
            .run(quiet=True, capture_stdout=True, cmd=self.__ffmpeg_cmd)
        )
        out = BytesIO(out)
        image = Image.open(out)

        return image

    def ffmpeg_version(self) -> Dict:
        return self.__ffmpeg_version(self.__local_dir)

    def __ffmpeg_version(self, local_dir: Optional[Path]) -> Dict:
        tools = ['ffmpeg', 'ffprobe']
        re_tools = '|'.join(tools)
        reg = re.compile(fr'({re_tools}) version (?P<version>[\d|.]*)')

        versions = {}

        for tool in tools:
            executable = str(local_dir / tool) if local_dir else tool
            args = [
                executable,
                '-version'
            ]

            process = None
            try:
                process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True)
            except:
                pass

            matches = None
            if process:
                stdout, _ = process.communicate()

                if stdout:
                    line: str = stdout.split('\n', 1)[0]
                    matches = reg.search(line)

            versions[tool] = matches.groupdict().get('version') if matches else None

        return versions
