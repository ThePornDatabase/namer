"""
Tools for working with files and directories in namer.
"""

import argparse
import sys
from pathlib import Path
from typing import Iterable, List, Optional

from loguru import logger

from namer.filenameparser import parse_file_name
from namer.types import default_config, NamerConfig, TargetFile


def is_interesting_movie(path: Optional[Path], config: NamerConfig) -> bool:
    if path is None:
        return False
    exists = path.exists()
    suffix = path.suffix.lower()[1:] in config.target_extensions
    size = path.stat().st_size / (1024 * 1024) >= config.min_file_size
    return exists and size and suffix


def gather_target_files_from_dir(dir_to_scan: Path, config: NamerConfig) -> Iterable[TargetFile]:
    """
    Find files to process in a target directory.
    """
    if dir_to_scan is not None and dir_to_scan.is_dir() and dir_to_scan.exists():
        logger.info("Scanning dir {} for sub-dirs/files to process", dir_to_scan)
        mapped: Iterable = map(lambda file: analyze((dir_to_scan / file), config), dir_to_scan.iterdir())
        filtered: Iterable[TargetFile] = filter(lambda file: file is not None, mapped)  # type: ignore
        return filtered
    return []


def __exact_parse(target_movie_file: Path, target_dir: Path, parse_dir: bool, config: NamerConfig) -> TargetFile:
    """
    Given a target movie file and a target containing directory, parse appropriate names as determined by
    config, aka, "prefer_dir_name_if_available".
    """
    target_file = TargetFile()
    target_file.target_directory = target_dir
    target_file.target_movie_file = target_movie_file
    target_file.parsed_dir_name = parse_dir
    if target_movie_file is not None:
        name = target_movie_file.name if not parse_dir else (target_dir.name + target_movie_file.suffix)
        target_file.parsed_file = parse_file_name(name, config.name_parser)
    return target_file


def find_target_file(root_dir: Path, config: NamerConfig) -> Path:
    """
    returns largest matching file
    """
    list_of_files = list(root_dir.rglob("**/*.*"))
    file = None
    if len(list_of_files) > 0:
        for target_ext in config.target_extensions:
            filtered = list(filter(lambda o, ext=target_ext: o.suffix is not None and o.suffix.lower()[1:] == ext, list_of_files))
            if file is None and filtered is not None and len(filtered) > 0:
                file = max(filtered, key=lambda x: x.stat().st_size)
    return file


def analyze(input_dir: Path, config: NamerConfig) -> Optional[TargetFile]:
    """
    after finding target directory and target movie from input, returns file name descriptors.
    """
    target_dir = input_dir if input_dir.is_dir() else input_dir.parent
    target_movie = input_dir if not input_dir.is_dir() else find_target_file(target_dir, config)
    parse_dir = input_dir.is_dir() and config.prefer_dir_name_if_available
    target_file = __exact_parse(target_movie, target_dir, parse_dir, config)
    target_file.input_file = input_dir
    output = target_file if is_interesting_movie(target_file.target_movie_file, config) else None
    return output


def attempt_analyze(input_dir: Optional[Path], config: NamerConfig) -> Optional[TargetFile]:
    """
    Attempts to parse an input path after determining target movies/directories
    """
    return None if input_dir is None else analyze(input_dir, config)


def main(arg_list: List[str]):
    """
    Attempt to parse a name.
    """
    description = "You are using the file name parser of the Namer project. Expects a single input, and will output the contents of FileNameParts, which is the internal input to the namer_metadatapi.py script. Output will be the representation of that FileNameParts.\n"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-f", "--file", help="String to parse for name parts", required=True)
    args = parser.parse_args(arg_list)
    target = Path(args.file).absolute()
    target_file = attempt_analyze(target, default_config())
    if target_file is not None:
        print(target_file.parsed_file)


if __name__ == "__main__":
    main(arg_list=sys.argv[1:])
