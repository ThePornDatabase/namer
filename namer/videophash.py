import concurrent.futures
import math
from pathlib import Path

from typing import Optional

import ffmpeg
import imagehash
from PIL import Image

from namer.ffmpeg import extract_screenshot


class VideoPerceptualHash:
    __screenshot_width: int = 160
    __columns: int = 5
    __rows: int = 5

    def get_phash(self, video: Path) -> Optional[imagehash.ImageHash]:
        phash = None

        thumbnail_list = self.__generate_thumbnails(video)
        if thumbnail_list:
            thumbnail_image = self.__concat_images(thumbnail_list)
            phash = imagehash.phash(thumbnail_image, hash_size=8, highfreq_factor=8)

        return phash

    def __generate_thumbnails(self, file: Path) -> list:
        probe = ffmpeg.probe(file)
        if not probe:
            return []

        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if video_stream is None:
            return []

        duration = float(probe['format']['duration'])
        duration = math.ceil(duration * 100.0) / 100.0
        chunk_count = self.__columns * self.__rows
        offset = 0.05 * duration
        step_size = (0.9 * duration) / chunk_count

        if duration / chunk_count < 0.03:
            return []

        images_queue = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for idx in range(chunk_count):
                time = offset + (idx * step_size)
                image = executor.submit(extract_screenshot, file, time, self.__screenshot_width)
                images_queue.append(image)

        concurrent.futures.wait(images_queue)
        images = [item.result() for item in images_queue]

        return images

    def __concat_images(self, images: list) -> Image:
        width, height = images[0].size

        image_size = (width * self.__columns, height * self.__rows)
        image = Image.new('RGB', image_size)

        for row in range(self.__rows):
            for col in range(self.__columns):
                offset = width * col, height * row
                idx = row * self.__columns + col
                image.paste(images[idx], offset)

        return image
