import concurrent.futures
import subprocess
import platform
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import List, Literal, Optional, Union

import json
import imagehash
import numpy
import oshash
import scipy.fft
import scipy.fftpack
from loguru import logger
from PIL import Image

from namer.ffmpeg import extract_screenshot, ffprobe


@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class PerceptualHash:
    duration: float
    phash: imagehash.ImageHash
    oshash: str


class VideoPerceptualHash:
    __screenshot_width: int = 160
    __columns: int = 5
    __rows: int = 5

    __home_path: Path = Path(__file__).parent
    __phash_path: Path = __home_path / 'tools'
    __phash_name: str = 'videohashes'
    __supported_arch: dict = {
        'amd64': 'amd64',
        'x86_64': 'amd64',
        'arm64': 'arm64',
        'aarch64': 'arm64',
        'arm': 'arm',
    }
    __phash_suffixes: dict = {
        'windows': '.exe',
        'linux': '-linux',
        'darwin': '-macos',
    }

    def __init__(self):
        if not self.__phash_path.is_dir():
            self.__phash_path.mkdir(exist_ok=True, parents=True)

        system = platform.system().lower()
        arch = platform.machine().lower()
        if arch not in self.__supported_arch.keys():
            raise SystemError(f"Unsupport architecture error {arch}")
        self.__phash_name += '-' + self.__supported_arch[arch] + self.__phash_suffixes[system]

    @lru_cache(maxsize=1024)
    def get_phash(self, file: Path) -> Optional[imagehash.ImageHash]:
        stat = file.stat()
        return self._get_phash(file, stat.st_size, stat.st_mtime)

    def _get_phash(self, file: Path, file_size: int, file_update: float) -> Optional[imagehash.ImageHash]:
        phash = None
        thumbnail_image = self.__generate_image_thumbnail(file)
        if thumbnail_image:
            phash = self.__phash(thumbnail_image, hash_size=8, high_freq_factor=8, resample=Image.Resampling.BILINEAR)  # type: ignore

        return phash

    def __generate_image_thumbnail(self, file: Path) -> Optional[Image.Image]:
        thumbnail_image = None

        probe = ffprobe(file)
        if not probe:
            return thumbnail_image

        duration = probe.get_format().duration

        thumbnail_list = self.__generate_thumbnails(file, duration)
        if thumbnail_list:
            thumbnail_image = self.__concat_images(thumbnail_list)

        return thumbnail_image

    def get_stash_phash(self, file: Path) -> Optional[PerceptualHash]:
        stat = file.stat()
        return self._get_stash_phash(file, stat.st_size, stat.st_mtime)

    @lru_cache(maxsize=1024)
    def _get_stash_phash(self, file: Path, file_size: int, file_update: float) -> Optional[PerceptualHash]:
        logger.info(f'Calculating phash for file "{file}"')
        return self.__execute_stash_phash(file)

    @lru_cache(maxsize=1024)
    def get_oshash(self, file: Path) -> str:
        stat = file.stat()
        return self._get_oshash(file, stat.st_size, stat.st_mtime)

    @lru_cache(maxsize=1024)
    def _get_oshash(self, file: Path, file_size: int, file_update: float) -> str:
        logger.info(f'Calculating oshash for file "{file}"')
        file_hash = oshash.oshash(str(file))
        return file_hash

    @staticmethod
    def return_perceptual_hash(duration: float, phash: Union[str, imagehash.ImageHash], file_oshash: str) -> PerceptualHash:
        output = PerceptualHash()
        output.duration = duration
        output.phash = imagehash.hex_to_hash(phash) if isinstance(phash, str) else phash
        output.oshash = file_oshash

        return output

    def __execute_stash_phash(self, file: Path) -> Optional[PerceptualHash]:
        output = None
        if not self.__phash_path:
            return output

        args = [
            str(self.__phash_path / self.__phash_name),
            '-json',
            '--video', str(file)
        ]
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True) as process:
            stdout, stderr = process.communicate()
            stdout, stderr = stdout.strip(), stderr.strip()

            success = process.returncode == 0
            if success:
                data = json.loads(stdout, object_hook=lambda d: SimpleNamespace(**d))
                output = self.return_perceptual_hash(data.duration, data.phash, data.oshash)
            else:
                logger.error(stderr)

        return output

    def __generate_thumbnails(self, file: Path, duration: float) -> List[Image.Image]:
        duration = int(Decimal(duration * 100).quantize(0, ROUND_HALF_UP)) / 100

        chunk_count = self.__columns * self.__rows
        offset = 0.05 * duration
        step_size = (0.9 * duration) / chunk_count

        if duration / chunk_count < 0.03:
            return []

        queue = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for idx in range(chunk_count):
                time = offset + (idx * step_size)
                future = executor.submit(extract_screenshot, file, time, self.__screenshot_width)
                queue.append(future)

        concurrent.futures.wait(queue)
        images = [item.result() for item in queue]

        return images

    def __concat_images(self, images: List[Image.Image]) -> Image.Image:
        width, height = images[0].size

        image_size = (width * self.__columns, height * self.__rows)
        image = Image.new('RGB', image_size)

        for row in range(self.__rows):
            for col in range(self.__columns):
                offset = width * col, height * row
                idx = row * self.__columns + col
                image.paste(images[idx], offset)

        return image

    @staticmethod
    def __phash(image: Image.Image, hash_size=8, high_freq_factor=4, resample: Literal[0, 1, 2, 3, 4, 5] = Image.Resampling.LANCZOS) -> Optional[imagehash.ImageHash]:  # type: ignore
        if hash_size < 2:
            raise ValueError("Hash size must be greater than or equal to 2")

        img_size = hash_size * high_freq_factor
        image = image.resize((img_size, img_size), resample).convert('L')
        pixels = numpy.asarray(image)

        dct = scipy.fft.dct(scipy.fft.dct(pixels, axis=0), axis=1)
        dct_low_freq = dct[:hash_size, :hash_size]  # type: ignore
        med = numpy.median(dct_low_freq)
        diff = dct_low_freq > med

        return imagehash.ImageHash(diff)
