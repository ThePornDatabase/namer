import concurrent.futures
import subprocess
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import List, Literal, Optional

import imagehash
import numpy
import scipy.fftpack
from loguru import logger
from PIL import Image

from namer.ffmpeg import extract_screenshot, ffprobe


class VideoPerceptualHash:
    __screenshot_width: int = 160
    __columns: int = 5
    __rows: int = 5

    __phash_path: Optional[Path]

    def __init__(self, phash_path: Path = None):
        self.__phash_path = phash_path

    def get_phash(self, file: Path) -> Optional[imagehash.ImageHash]:
        phash = None

        probe = ffprobe(file)
        if not probe:
            return

        duration = probe.get_format().duration

        thumbnail_list = self.__generate_thumbnails(file, duration)
        if thumbnail_list:
            thumbnail_image = self.__concat_images(thumbnail_list)
            phash = self.__phash(thumbnail_image, hash_size=8, high_freq_factor=8, resample=Image.Resampling.BILINEAR)

        return phash

    def get_stash_phash(self, file: Path) -> Optional[imagehash.ImageHash]:
        return self.__execute_stash_phash(file)

    def __execute_stash_phash(self, file: Path) -> Optional[imagehash.ImageHash]:
        phash = None
        if not self.__phash_path:
            return phash

        args = [
            str(self.__phash_path),
            '-f', str(file),
        ]
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True) as process:
            stdout, stderr = process.communicate()
            stdout, stderr = stdout.strip(), stderr.strip()
            success = process.returncode == 0
            if success:
                phash = imagehash.hex_to_hash(stdout)
            else:
                logger.error(stderr)

        return phash

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
    def __phash(image: Image.Image, hash_size=8, high_freq_factor=4, resample: Literal[0, 1, 2, 3, 4, 5] = Image.Resampling.LANCZOS) -> Optional[imagehash.ImageHash]:
        if hash_size < 2:
            raise ValueError("Hash size must be greater than or equal to 2")

        img_size = hash_size * high_freq_factor
        image = image.resize((img_size, img_size), resample).convert('L')
        pixels = numpy.asarray(image)

        dct = scipy.fft.dct(scipy.fft.dct(pixels, axis=0), axis=1)
        dct_low_freq = dct[:hash_size, :hash_size]
        med = numpy.median(dct_low_freq)
        diff = dct_low_freq > med

        return imagehash.ImageHash(diff)
