"""
Tools for working with files and directories in namer.
"""

import argparse
from platform import system
import os
import shutil
import sys
from pathlib import Path
from typing import Iterable, List, Optional

from loguru import logger

from namer.filenameparser import parse_file_name
from namer.types import ComparisonResult, LookedUpFileInfo, default_config, NamerConfig, TargetFile


def write_log_file(movie_file: Optional[Path], match_attempts: Optional[List[ComparisonResult]], namer_config: NamerConfig) -> Optional[Path]:
    """
    Given porndb scene results sorted by how closely they match a file,  write the contents
    of the result matches to a log file.
    """
    log_name = None
    if movie_file is not None:
        log_name = movie_file.with_name(movie_file.stem + "_namer.log")
        logger.info("Writing log to {}", log_name)
        with open(log_name, "wt", encoding="utf-8") as log_file:
            if match_attempts is None or len(match_attempts) == 0:
                log_file.write("No search results returned.\n")
            else:
                for attempt in match_attempts:
                    log_file.write("\n")
                    log_file.write(f"File                : {attempt.name_parts.source_file_name}\n")
                    log_file.write(f"Scene Name          : {attempt.looked_up.name}\n")
                    log_file.write(f"Match               : {attempt.is_match()}\n")
                    log_file.write(f"Query URL           : {attempt.looked_up.original_query}\n")
                    if attempt.name_parts.site is None:
                        attempt.name_parts.site = "None"
                    if attempt.name_parts.date is None:
                        attempt.name_parts.date = "None"
                    if attempt.name_parts.date is None:
                        attempt.name_parts.name = "None"
                    log_file.write(f"{str(attempt.site_match):5} Found Site Name: {attempt.looked_up.site:50.50} Parsed Site Name: {attempt.name_parts.site:50.50}\n")
                    log_file.write(f"{str(attempt.date_match):5} Found Date    : {attempt.looked_up.date:50.50} Parsed Date    : {attempt.name_parts.date:50.50}\n")
                    log_file.write(f"{attempt.name_match:5.1f} Found Name    : {attempt.name:50.50} Parsed Name    : {attempt.name_parts.name:50.50}\n")
        set_permissions(log_name, namer_config)
    return log_name


def _set_perms(target: Path, config: NamerConfig):
    file_perm: Optional[int] = (None if config.set_file_permissions is None else int(str(config.set_file_permissions), 8))
    dir_perm: Optional[int] = (None if config.set_dir_permissions is None else int(str(config.set_dir_permissions), 8))
    if config.set_gid is not None:
        os.lchown(target, uid=-1, gid=config.set_gid)
    if config.set_uid is not None:
        os.lchown(target, uid=config.set_uid, gid=-1)
    if target.is_dir() and dir_perm is not None:
        target.chmod(dir_perm)
    elif target.is_file() and file_perm is not None:
        target.chmod(file_perm)


def set_permissions(file: Optional[Path], config: NamerConfig):
    """
    Given a file or dir, set permissions from NamerConfig.set_file_permissions,
    NamerConfig.set_dir_permissions, and uid/gid if set for the current process recursively.
    """
    if system() != "Windows" and file is not None and file.exists() and config.update_permissions_ownership is True:
        _set_perms(file, config)
        if file.is_dir():
            for target in file.rglob("*.*"):
                _set_perms(target, config)


def move_to_final_location(target_files: TargetFile,
                           new_metadata: LookedUpFileInfo,
                           inplace: bool,
                           config: NamerConfig) -> TargetFile:
    """
    Moves a file or directory to it's final location after verifying there is no collision.
    Should a collision occur, the file is appropriately renamed to avoid collision.
    """
    infix = 0

    name_template = config.inplace_name
    inputed_dir = target_files.input_file == target_files.target_directory

    target_dir = target_files.target_directory
    name_template = config.inplace_name
    containing_dir = target_files.target_directory
    movie_name = None
    relative_path = None

    # will we rename or move an inputed directory?
    if (inputed_dir and inplace) or not inplace:
        # if dir is inputed it may be moved with relative name.
        name_template = config.new_relative_path_name
        # this is not an inplace move, will send to the dest dir.
        target_dir = target_dir.parent if inplace else config.dest_dir

    # determine where to move the movie file.
    if target_files.target_movie_file is not None:
        while True:
            relative_path = Path(new_metadata.new_file_name(name_template, f"({infix})"))
            movie_name = target_dir / relative_path
            movie_name = movie_name.resolve()
            infix += 1
            if not movie_name.exists() or target_files.target_movie_file.samefile(movie_name):
                break

        movie_name.parent.mkdir(exist_ok=True, parents=True)
        target_files.target_movie_file.rename(movie_name)

    if relative_path is not None:
        containing_dir = target_dir / relative_path.parts[0]

    # we want to retain files if asked and if a directory will exist.
    if ((inputed_dir and inplace) or not inplace) and relative_path is not None:
        if not config.del_other_files and len(relative_path.parts) > 1:
            containing_dir = target_dir / relative_path.parts[0]
            containing_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"moving other files to new dir: {containing_dir} from {target_files.target_directory}")
            # first remove namer log if exists
            possible_log = target_files.target_movie_file.parent / (target_files.target_movie_file.stem + "_namer.log")
            if possible_log.exists():
                possible_log.unlink()
            # move directory contents
            for file in target_files.target_directory.iterdir():
                full_file = target_files.target_directory / file
                if full_file != target_files.target_movie_file:
                    dest_file = containing_dir / file
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    full_file.rename(dest_file)

    if relative_path is not None and len(relative_path.parts) > 1:
        set_permissions(target_dir / relative_path.parts[0], config)
    else:
        set_permissions(movie_name, config)

    output = TargetFile()
    if movie_name is not None:
        output.target_movie_file = movie_name
        output.input_file = movie_name
    if containing_dir is not None:
        output.target_directory = containing_dir
        if containing_dir != target_dir:
            output.input_file = containing_dir

    if target_files.input_file == target_files.target_directory and not subpath_or_equal(output.target_directory, target_files.target_directory):
        shutil.rmtree(target_files.target_directory)
    return output


def subpath_or_equal(potential_sub: Path, potential_parent: Path) -> bool:
    return potential_sub == potential_parent or str(potential_sub.absolute()).startswith(str(potential_parent.absolute()))


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
