import subprocess
import platform
from dataclasses import dataclass
from functools import lru_cache
from json import JSONDecodeError
from pathlib import Path
from types import SimpleNamespace
from typing import Optional, Union

import json
import imagehash
from loguru import logger


@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class PerceptualHash:
    duration: int
    phash: imagehash.ImageHash
    oshash: str


def return_perceptual_hash(duration: Union[float, int], phash: Optional[Union[str, imagehash.ImageHash]], file_oshash: str) -> PerceptualHash:
    output = PerceptualHash()
    output.duration = int(duration) if isinstance(duration, float) else duration
    if phash:
        output.phash = imagehash.hex_to_hash(phash) if isinstance(phash, str) else phash
    output.oshash = file_oshash

    return output


class StashVideoPerceptualHash:
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
            raise SystemError(f"Unsupported architecture error {arch}")

        self.__phash_name += '-' + self.__supported_arch[arch] + self.__phash_suffixes[system]

    def install_ffmpeg(self) -> None:
        # videohasher installs ffmpeg next to itself by default, even if
        # there's nothing to process.
        self.__execute_stash_phash(None)

    def get_hashes(self, file: Path) -> Optional[PerceptualHash]:
        stat = file.stat()
        return self._get_stash_phash(file, stat.st_size, stat.st_mtime)

    @lru_cache(maxsize=1024)
    def _get_stash_phash(self, file: Path, file_size: int, file_update: float) -> Optional[PerceptualHash]:
        logger.info(f'Calculating phash for file "{file}"')
        return self.__execute_stash_phash(file)

    def __execute_stash_phash(self, file: Optional[Path]) -> Optional[PerceptualHash]:
        output = None
        if not self.__phash_path:
            return output

        args = [
            str(self.__phash_path / self.__phash_name),
            '-json',
        ]
        if file:
            args.append('--video')
            args.append(str(file))
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True) as process:
            stdout, stderr = process.communicate()
            stdout, stderr = stdout.strip(), stderr.strip()

            success = process.returncode == 0
            if success:
                data = None
                try:
                    data = json.loads(stdout, object_hook=lambda d: SimpleNamespace(**d))
                except JSONDecodeError:
                    logger.error(stdout)
                    pass

                if data:
                    output = return_perceptual_hash(data.duration, data.phash, data.oshash)
            elif file:
                logger.error(stderr)

        return output
