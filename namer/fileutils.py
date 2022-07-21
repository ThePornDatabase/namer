"""
Tools for working with files and directories in namer.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
from platform import system
from typing import Iterable, List, Optional

from loguru import logger

from namer.ffmpeg import ffprobe
from namer.filenameparser import parse_file_name
from namer.types import Command, ComparisonResult, default_config, LookedUpFileInfo, NamerConfig


def move_command_files(target: Optional[Command], new_target: Path) -> Optional[Command]:
    working_dir = None
    working_file = None
    output: Optional[Command] = None
    if target is None:
        return None

    if target.input_file == target.target_directory and target.target_directory is not None:
        working_dir = Path(new_target) / target.target_directory.name
        logger.info("Moving {} to {} for processing", target.target_directory, working_dir)
        shutil.move(target.target_directory, working_dir)
        output = make_command(working_dir, target.config)
    else:
        working_file = Path(new_target) / target.target_movie_file.name
        target.target_movie_file.rename(working_file)
        logger.info("Moving {} to {} for processing", target.target_movie_file, working_file)
        output = make_command(working_file, target.config)
    if output is not None:
        output.tpdb_id = target.tpdb_id
        output.inplace = target.inplace
        output.write_from_nfos = target.write_from_nfos
    return output


def write_log_file(movie_file: Optional[Path], match_attempts: Optional[List[ComparisonResult]], namer_config: NamerConfig) -> Optional[Path]:
    """
    Given porndb scene results sorted by how closely they match a file,  write the contents
    of the result matches to a log file.
    """
    log_name = None
    if movie_file is not None:
        log_name = movie_file.with_name(movie_file.stem + "_namer.log")
        logger.info("Writing log to {}", log_name)
        with open(log_name, "wt", encoding="UTF-8") as log_file:
            if match_attempts is None or len(match_attempts) == 0:
                log_file.write("No search results returned.\n")
            else:
                for attempt in match_attempts:
                    log_file.write("\n")
                    log_file.write(f"File                 : {attempt.name_parts.source_file_name}\n")
                    log_file.write(f"Scene Name           : {attempt.looked_up.name}\n")
                    log_file.write(f"Match                : {attempt.is_match()}\n")
                    log_file.write(f"Query URL            : {attempt.looked_up.original_query}\n")
                    if attempt.name_parts.site is None:
                        attempt.name_parts.site = "None"
                    if attempt.name_parts.date is None:
                        attempt.name_parts.date = "None"
                    if attempt.name_parts.date is None:
                        attempt.name_parts.name = "None"
                    log_file.write(f"{str(attempt.site_match):5} Found Site Name: {attempt.looked_up.site:50.50} Parsed Site Name: {attempt.name_parts.site:50.50}\n")
                    log_file.write(f"{str(attempt.date_match):5} Found Date     : {attempt.looked_up.date:50.50} Parsed Date     : {attempt.name_parts.date:50.50}\n")
                    log_file.write(f"{attempt.name_match:5.1f} Found Name     : {attempt.name:50.50} Parsed Name     : {attempt.name_parts.name:50.50}\n")
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
            for target in file.rglob("**/*"):
                _set_perms(target, config)


def move_to_final_location(command: Command, new_metadata: LookedUpFileInfo) -> Command:
    """
    Moves a file or directory to its final location after verifying there is no collision.
    Should a collision occur, the file is appropriately renamed to avoid collision.
    """
    infix = 0

    # determine where we will move the movie, and how we will name it.
    # if in_place is False we will move it to the config defined destination dir.
    # if a directory name was passed in we will rename the dir with the relative_path_name from the config
    # else we will just rename the movie in its current location (as all that was defined in the command was the movie file.)
    name_template = command.config.inplace_name
    target_dir = command.target_movie_file.parent
    if command.target_directory is not None:
        name_template = command.config.new_relative_path_name
        target_dir = command.target_directory.parent
    if command.inplace is not True:
        name_template = command.config.new_relative_path_name
        target_dir = command.config.dest_dir

    relative_path: Optional[Path] = None
    # Find non-conflicting movie name.
    while True:
        relative_path = Path(new_metadata.new_file_name(name_template, f"({infix})"))
        movie_name = target_dir / relative_path
        movie_name = movie_name.resolve()
        infix += 1
        if not movie_name.exists() or command.target_movie_file.samefile(movie_name):
            break

    # Create the new dir if needed and move the movie file to it.
    movie_name.parent.mkdir(exist_ok=True, parents=True)
    command.target_movie_file.rename(movie_name)

    containing_dir: Optional[Path] = None
    if len(relative_path.parts) > 1:
        containing_dir = target_dir / relative_path.parts[0]

    # we want to retain files if asked and if a directory will exist.
    if command.target_directory and not command.config.del_other_files and containing_dir is not None:
        containing_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"moving other files to new dir: {containing_dir} from {command.target_directory}")
        # first remove namer log if exists
        possible_log = command.target_movie_file.parent / (command.target_movie_file.stem + "_namer.log")
        if possible_log.exists():
            possible_log.unlink()
        # move directory contents
        for file in command.target_directory.iterdir():
            full_file = command.target_directory / file
            if full_file != command.target_movie_file:
                dest_file = containing_dir / file
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                full_file.rename(dest_file)
    if command.target_directory and containing_dir:
        set_permissions(containing_dir, command.config)
    else:
        set_permissions(movie_name, command.config)

    output = Command()
    if movie_name is not None:
        output.target_movie_file = movie_name
        output.input_file = movie_name
    if containing_dir is not None:
        output.target_directory = containing_dir
        output.input_file = containing_dir

    if command.target_directory is not None and not subpath_or_equal(output.target_directory, command.target_directory):
        shutil.rmtree(command.target_directory)
    return output


def subpath_or_equal(potential_sub: Optional[Path], potential_parent: Optional[Path]) -> bool:
    if potential_parent is None or potential_sub is None:
        return False
    return len(potential_parent.parts) <= len(potential_sub.parts) and all(i == j for i, j in zip(potential_parent.parts, potential_sub.parts))


def is_interesting_movie(path: Optional[Path], config: NamerConfig) -> bool:
    if path is None:
        return False
    exists = path.exists()
    suffix = path.suffix.lower()[1:] in config.target_extensions
    size = path.stat().st_size / (1024 * 1024) >= config.min_file_size
    return exists and size and suffix


def gather_target_files_from_dir(dir_to_scan: Path, config: NamerConfig) -> Iterable[Command]:
    """
    Find files to process in a target directory.
    """
    if dir_to_scan is not None and dir_to_scan.is_dir() and dir_to_scan.exists():
        logger.info("Scanning dir {} for sub-dirs/files to process", dir_to_scan)
        mapped: Iterable = map(lambda file: make_command((dir_to_scan / file), config), dir_to_scan.iterdir())
        filtered: Iterable[Command] = filter(lambda file: file is not None, mapped)  # type: ignore
        return filtered
    return []


def __exact_command(target_movie_file: Path, target_dir: Optional[Path], config: NamerConfig) -> Command:
    """
    Given a target movie file and a target containing directory, parse appropriate names as determined by
    config, aka, "prefer_dir_name_if_available".
    """
    command = Command()
    command.target_directory = target_dir
    command.target_movie_file = target_movie_file
    command.parsed_dir_name = target_dir is not None and config.prefer_dir_name_if_available
    command.config = config
    name = target_movie_file.name
    parsed_dir_name = False
    if target_dir is not None and config.prefer_dir_name_if_available:
        name = target_dir.name + target_movie_file.suffix
        parsed_dir_name = True
    command.parsed_file = parse_file_name(name, config.name_parser)
    command.parsed_dir_name = parsed_dir_name
    return command


def find_target_file(root_dir: Path, config: NamerConfig) -> Optional[Path]:
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


def make_command(input_file: Path, config: NamerConfig, nfo: bool = False, inplace: bool = False, uuid: Optional[str] = None) -> Optional[Command]:
    """
    after finding target directory and target movie from input, returns file name descriptors.
    """
    target_dir = input_file if input_file.is_dir() else None
    target_movie = input_file if not input_file.is_dir() else find_target_file(input_file, config)
    if target_movie is None:
        return None
    target_file = __exact_command(target_movie, target_dir, config)
    target_file.input_file = input_file
    target_file.tpdb_id = uuid
    target_file.write_from_nfos = nfo
    target_file.inplace = inplace
    target_file.ff_probe_results = ffprobe(target_movie)
    output = target_file if is_interesting_movie(target_file.target_movie_file, config) else None
    return output


def make_command_relative_to(input_dir: Path, relative_to: Path, config: NamerConfig, nfo: bool = False, inplace: bool = False, uuid: Optional[str] = None) -> Optional[Command]:
    """
    Ensure we are going to handle the directory relative to another directory, rather than just the file
    specified
    """
    if subpath_or_equal(input_dir, relative_to):
        relative_path = input_dir.absolute().relative_to(relative_to.absolute())
        if relative_path is not None:
            target_file = relative_to / relative_path.parts[0]
            return make_command(target_file, config, nfo, inplace, uuid)
    return None


def main(arg_list: List[str]):
    """
    Attempt to parse a name.
    """
    description = "You are using the file name parser of the Namer project. Expects a single input, and will output the contents of FileNameParts, which is the internal input to the namer_metadatapi.py script. Output will be the representation of that FileNameParts.\n"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-f", "--file", help="String to parse for name parts", required=True)
    args = parser.parse_args(arg_list)
    target = Path(args.file).absolute()
    target_file = make_command(target, default_config())
    if target_file is not None:
        print(target_file.parsed_file)


if __name__ == "__main__":
    main(arg_list=sys.argv[1:])
