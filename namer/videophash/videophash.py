import concurrent.futures
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from pathlib import Path
from typing import List, Literal, Optional

import imagehash
import numpy
import oshash
import scipy.fft
import scipy.fftpack
from loguru import logger
from PIL import Image

from namer.ffmpeg import FFMpeg
from namer.videophash import PerceptualHash, return_perceptual_hash


class VideoPerceptualHash:
    __screenshot_width: int = 160
    __columns: int = 5
    __rows: int = 5

    __ffmpeg: FFMpeg

    def __init__(self, ffmpeg: FFMpeg):
        self.__ffmpeg = ffmpeg

    def get_hashes(self, file: Path, max_workers: Optional[int] = None, use_gpu: bool = False) -> Optional[PerceptualHash]:
        data = None

        probe = self.__ffmpeg.ffprobe(file)
        if not probe:
            return data

        duration = probe.get_format().duration
        phash = self.get_phash(file, duration, max_workers, use_gpu)
        if phash:
            file_oshash = self.get_oshash(file)

            data = return_perceptual_hash(duration, phash, file_oshash)

        return data

    def get_phash(self, file: Path, duration: float, max_workers: Optional[int], use_gpu: bool) -> Optional[imagehash.ImageHash]:
        stat = file.stat()
        return self._get_phash(file, duration, max_workers, use_gpu, stat.st_size, stat.st_mtime)

    @lru_cache(maxsize=1024)  # noqa: B019
    def _get_phash(self, file: Path, duration: float, max_workers: Optional[int], use_gpu: bool, file_size: int, file_update: float) -> Optional[imagehash.ImageHash]:
        logger.info(f'Calculating phash for file "{file}"')
        phash = self.__calculate_phash(file, duration, max_workers, use_gpu)
        return phash

    def __calculate_phash(self, file: Path, duration: float, max_workers: Optional[int], use_gpu: bool) -> Optional[imagehash.ImageHash]:
        phash = None

        thumbnail_image = self.__generate_image_thumbnail(file, duration, max_workers, use_gpu)
        if thumbnail_image:
            phash = self.__phash(thumbnail_image, hash_size=8, high_freq_factor=8, resample=Image.Resampling.BILINEAR)  # type: ignore

        return phash

    def __generate_image_thumbnail(self, file: Path, duration: float, max_workers: Optional[int], use_gpu: bool) -> Optional[Image.Image]:
        thumbnail_image = None

        thumbnail_list = self.__generate_thumbnails(file, duration, max_workers, use_gpu)
        if thumbnail_list:
            thumbnail_image = self.__concat_images(thumbnail_list)

        return thumbnail_image

    def get_oshash(self, file: Path) -> str:
        stat = file.stat()
        return self._get_oshash(file, stat.st_size, stat.st_mtime)

    @lru_cache(maxsize=1024)  # noqa: B019
    def _get_oshash(self, file: Path, file_size: int, file_update: float) -> str:
        logger.info(f'Calculating oshash for file "{file}"')
        file_hash = oshash.oshash(str(file))
        return file_hash

    def __generate_thumbnails(self, file: Path, duration: float, max_workers: Optional[int], use_gpu: bool) -> List[Image.Image]:
        duration = int(Decimal(duration * 100).quantize(0, ROUND_HALF_UP)) / 100

        chunk_count = self.__columns * self.__rows
        offset = 0.05 * duration
        step_size = (0.9 * duration) / chunk_count

        if duration / chunk_count < 0.03:
            return []

        queue = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for idx in range(chunk_count):
                time = offset + (idx * step_size)
                future = executor.submit(self.__ffmpeg.extract_screenshot, file, time, self.__screenshot_width, use_gpu)
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
