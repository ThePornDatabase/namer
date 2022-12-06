import concurrent.futures
import subprocess
import platform
import shutil
from importlib import resources
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from types import SimpleNamespace
from typing import List, Literal, Optional

import json
import imagehash
import numpy
import scipy.fft
import scipy.fftpack
from loguru import logger
from PIL import Image

from namer.ffmpeg import extract_screenshot, ffprobe


class VideoPerceptualHash:
    __screenshot_width: int = 160
    __columns: int = 5
    __rows: int = 5

    __phash_path: Path
    __phash_name: str = 'videohash'

    def __init__(self):
        self.__phash_path = Path(__file__).parent.parent / 'tools'
        if not self.__phash_path.is_dir():
            self.__phash_path.mkdir(exist_ok=True, parents=True)
        if not [file for file in self.__phash_path.glob('*') if self.__phash_name == file.stem]:
            self.__prepare_stash_phash()

    def get_phash(self, file: Path) -> Optional[imagehash.ImageHash]:
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

    def get_stash_phash(self, file: Path) -> Optional[imagehash.ImageHash]:
        return self.__execute_stash_phash(file)

    def copy_resource_to_file(self, full_path: str, output: Path) -> bool:
        parts = full_path.split('/')
        if hasattr(resources, 'files'):
            trav = resources.files(parts[0])
            for part in parts[1:]:
                trav = trav.joinpath(part)
            with trav.open("rb") as bin, open(output, mode="+bw") as out:
                shutil.copyfileobj(bin, out)
                return True
        if hasattr(resources, 'open_binary'):
            with resources.open_binary(".".join(parts[0:-1]), parts[-1]) as bin, open(output, mode="+bw") as out:
                shutil.copyfileobj(bin, out)
                return True
        return False

    def __prepare_stash_phash(self):
        os = platform.system().lower()
        success = False
        post: str = '.exe'
        if os == "linux":
            post = '-linux'
        elif os == 'darwin':
            post = '-macos'
        if self.__phash_path:
            success = self.copy_resource_to_file('namer/videohashtools/videohashes' + post, self.__phash_path / self.__phash_name)
            if os != 'windows' and self.__phash_path and success:
                file = self.__phash_path / self.__phash_name
                file.chmod(0o777)
        return success

    def __execute_stash_phash(self, file: Path) -> Optional[imagehash.ImageHash]:
        output = None
        if not self.__phash_path:
            return output

        args = [str(self.__phash_path / self.__phash_name), '-json', '--video', str(file)]
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True) as process:
            stdout, stderr = process.communicate()
            stdout, stderr = stdout.strip(), stderr.strip()
            success = process.returncode == 0
            if success:
                print(stdout)
                data = json.loads(stdout, object_hook=lambda d: SimpleNamespace(**d))
                # duration = data.duration
                phash = data.phash
                # oshash = data.oshash
                output = imagehash.hex_to_hash(phash)
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
