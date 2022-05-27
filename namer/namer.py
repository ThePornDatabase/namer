"""
This file can process individual movie files in place.
There name, or directory name, will be analyzed, matched against
the porndb, and used for renaming (in place), and updating a mp4
file's metadata (poster, artists, etc.)
"""
import argparse
import pathlib
import string
import sys
from pathlib import Path
from random import choices
from typing import List, Optional

from loguru import logger

from namer.filenameparser import parse_file_name
from namer.fileutils import find_target_file, move_command_files, move_to_final_location, set_permissions, write_log_file
from namer.metadataapi import get_image, get_trailer, match, get_complete_metadatapi_net_fileinfo
from namer.moviexml import parse_movie_xml_file, write_nfo
from namer.mutagen import update_mp4_file
from namer.types import ComparisonResult, Command, default_config, from_config, LookedUpFileInfo, NamerConfig

DESCRIPTION = """
    Namer, the porndb local file renamer. It can be a command line tool to rename mp4/mkv/avi/mov/flv files and to embed tags in mp4s,
    or a watchdog service to do the above watching a directory for new files and moving matched files to a target location.
    File names are assumed to be of the form SITE.[YY]YY.MM.DD.String.of.performers.and.or.scene.name.<IGNORED_INFO>.[mp4|mkv].
    In the name, read the periods, ".", as any number of spaces " ", dashes "-", or periods ".".

    Provided you have an access token to the porndb (free sign up) https://www.metadataapi.net/, this program will
    attempt to match your file's name to search results from the porndb.   Please note that the site must at least be
    a substring of the actual site name on the porndb, and the date must be within one day or the release date on the
    porndb for a match to be considered.  If the log file flag is enabled then a <original file name minus ext>_namer.log
    file will be written with all the potential matches sorted, descending by how closely the scene name/performer names
    match the file's name segment after the 'SITE.[YY]YY.MM.DD'.
  """


def dir_with_sub_dirs_to_process(dir_to_scan: Path, config: NamerConfig, infos: bool = False):
    """
    Used to find sub-dirs of a directory to be individually processed.
    The directories will be scanned for media and named/tagged in place
    based on config settings.
    """
    if dir_to_scan is not None and dir_to_scan.is_dir() and dir_to_scan.exists():
        logger.info("Scanning dir {} for sub-dirs/files to process", dir_to_scan)
        files = list(dir_to_scan.iterdir())
        files.sort()
        for file in files:
            fullpath_file = dir_to_scan / file
            if fullpath_file.is_dir() or fullpath_file.suffix.upper() in [".MP4", ".MKV"]:
                command = determine_target_file(fullpath_file, config, nfo=infos, inplace=True)
                process_file(command)


def tag_in_place(video: Optional[Path], config: NamerConfig, new_metadata: LookedUpFileInfo):
    """
    Uses ComparisonResults to update a mp4 file's metadata based on a match in
    ComparisonResults.   Expects the first item of list to be the match if there is one.
    Will download a poster as well depending on NamerConfig config setting.
    """
    if new_metadata is not None and video is not None:
        poster = None
        if config.enabled_tagging is True and video.suffix.lower() == ".mp4":
            random = "".join(choices(population=string.ascii_uppercase + string.digits, k=10))
            poster = get_image(new_metadata.poster_url, random, video, config)
            logger.info("Updating file metadata (atoms): {}", video)
            update_mp4_file(video, new_metadata, poster, config)
        logger.info("Done tagging file: {}", video)
        if poster is not None and new_metadata.poster_url is not None and new_metadata.poster_url.startswith("http"):
            poster.unlink()


def determine_target_file(file_to_process: Path, config: NamerConfig, nfo: bool, inplace: bool) -> Command:
    """
    Base on the file to process - which may be a file or a dir, and configuration, determine
    the file if needed (largest mp4, or mkv in a directory), or the directory (parent dir of file),
    as well as determine which should be used for attempted naming.

    If config.prefer_dir_name_if_available is set to True and a directory was passed as file_to_process
    then the directory's name will be returned as name, else the found file's name is used.
    """
    command = Command()
    containing_dir = None
    if file_to_process.is_dir():
        logger.info("Target dir: {}", file_to_process)
        containing_dir = file_to_process
        command.target_directory = containing_dir
        command.target_movie_file = find_target_file(file_to_process, config)
    else:
        command.target_movie_file = file_to_process
        command.target_directory = None

    if config.prefer_dir_name_if_available and containing_dir is not None:
        name = containing_dir.name + command.target_movie_file.suffix
    else:
        name = command.target_movie_file.name
    logger.info("file: {}", command.target_movie_file)
    logger.info("dir : {}", containing_dir)
    command.input_file = file_to_process
    command.parsed_file = parse_file_name(name, config.name_parser)
    command.inplace = inplace
    command.write_from_nfos = nfo
    command.config = config
    return command


def get_local_metadata_if_requested(video_file: Path) -> Optional[LookedUpFileInfo]:
    """
    If there is an .nfo file next to the video_file, attempt to read it as
    an Emby/Jellyfin style movie xml file.
    """
    nfo_file = video_file.parent / (video_file.stem + ".nfo")
    if nfo_file.is_file() and nfo_file.exists():
        return parse_movie_xml_file(nfo_file)
    return None


def process_file(command: Command) -> Optional[Command]:
    """
    Bread and butter method.
    Given a file, determines if it's a dir, if so, the dir name may be used
    for comparison with the porndb.   The larges mp4/mkv file in the directory
    or any subdirectories will be assumed to be the movie file.

    Does not properly handle multipart movies.

    If the input file is not a dir it's name will be used, and it is assumed to
    be the movie file we wish to tag.

    The movie is either renamed in place if a file, or renamed and move to the root
    of the dir if a dir was passed in.

    The file is then update based on the metadata from the porndb if a mp4.
    """
    logger.info("Processing: {}", command.input_file)
    if command.target_movie_file is not None:
        new_metadata: Optional[LookedUpFileInfo] = None
        search_results: List[ComparisonResult] = []
        # Match to nfo files, if enabled and found.
        if command.write_from_nfos is True:
            new_metadata = get_local_metadata_if_requested(command.target_movie_file)
            if new_metadata is not None:
                new_metadata.original_parsed_filename = command.parsed_file
            else:
                logger.error("""
                        Could not process files: {}
                        In the file's name should start with a site, a date and end with an extension""", command.input_file)
        elif new_metadata is None and command.tpdbid is not None and command.parsed_file is not None:
            search_results = []
            file_infos = get_complete_metadatapi_net_fileinfo(command.parsed_file, command.tpdbid, command.config)
            if file_infos is not None:
                new_metadata = file_infos
        elif new_metadata is None and command.parsed_file is not None and command.parsed_file.name is not None:
            search_results = match(command.parsed_file, command.config)
            if len(search_results) > 0 and search_results[0].is_match() is True:
                new_metadata = search_results[0].looked_up
            if not command.target_movie_file:
                logger.error("""
                    Could not process file or directory: {}
                    Likely attempted to use the directory's name as the name to parse.
                    In general the dir or file's name should start with a site, a date and end with an extension
                    Target video file in dir was: {}""", command.input_file, command.target_movie_file)
        target_dir = command.target_directory if command.target_directory is not None else command.target_movie_file.parent
        set_permissions(target_dir, command.config)
        if new_metadata is not None:
            target = move_to_final_location(command, new_metadata)
            tag_in_place(target.target_movie_file, command.config, new_metadata)
            add_extra_artifacts(target.target_movie_file, new_metadata, search_results, command.config)
            logger.info("Done processing file: {}, moved to {}", command.target_movie_file, target.target_movie_file)
            return target
        elif command.inplace is False:
            failed = move_command_files(command, command.config.failed_dir)
            if failed is not None and search_results is not None:
                write_log_file(failed.target_movie_file, search_results, failed.config)
    return None


def add_extra_artifacts(video_file: Path, new_metadata: LookedUpFileInfo, search_results: List[ComparisonResult], config: NamerConfig):
    """
    Once the file is in its final location we will grab other relevant output if requested.
    """
    trailer = None
    if config.write_namer_log is True:
        write_log_file(video_file, search_results, config)
    if config.trailer_location is not None and not len(config.trailer_location) == 0 and new_metadata is not None:
        trailer = get_trailer(new_metadata.trailer_url, video_file, config)
    if config.write_nfo and new_metadata is not None:
        poster = get_image(new_metadata.poster_url, "-poster", video_file, config)
        background = get_image(new_metadata.background_url, "-background", video_file, config)
        for performer in new_metadata.performers:
            poster = get_image(performer.image, performer.name.replace(" ", "-") + "-image", video_file, config)
            if poster is not None:
                performer.image = str(poster)
        write_nfo(video_file, new_metadata, config, trailer, poster, background)


def check_arguments(file_to_process: Path, dir_to_process: Path, config_override: Path):
    """
    check arguments.
    """
    error = False
    if file_to_process is not None:
        logger.info("File to process: {}", file_to_process)
        if not file_to_process.is_file() or not file_to_process.exists():
            logger.error("Error not a file! {}", file_to_process)
            error = True

    if dir_to_process is not None:
        logger.info("Directory to process: {}", dir_to_process)
        if not dir_to_process.is_dir() or not dir_to_process.exists():
            logger.info("Error not a directory! {}", dir_to_process)
            error = True

    if config_override is not None:
        logger.info("Config override specified: {}", config_override)
        if not config_override.is_file() or not config_override.exists():
            logger.info("Config override specified, but file does not exit: {}", config_override)
            error = True
    return error


def main(arg_list: List[str]):
    """
    Used to tag and rename files from the command line.
    See usage function above.
    """
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("-c", "--configfile", type=pathlib.Path, help="config file, defaults first to env var NAMER_CONFIG, then local path namer.cfg, and finally ~/.namer.cfg.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--file", type=Path, help="a single file to process, and rename.")
    group.add_argument("-d", "--dir", type=Path, help="a directory to process.")
    parser.add_argument("-m", "--many", action="store_true", help="if set, a directory have all it's sub directories processed. Files move only within sub dirs, or are renamed in place, if in the root dir to scan")
    parser.add_argument("-i", "--infos", action="store_true", help="if set, .nfo files will attempt to be accessed next to movie files, if info files are found and parsed successfully, that metadata will be used rather than porndb matching. If using jellyfin .nfo files, please bump your release date by one day until they fix this issue: https://github.com/jellyfin/jellyfin/issues/7271.")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose, print logs")
    args = parser.parse_args(arg_list)
    level = "DEBUG" if args.verbose else "ERROR"
    logger.remove()
    logger.add(sys.stdout, format="{time} {level} {message}", level=level)
    check_arguments(args.file, args.dir, args.configfile)

    config = default_config()
    if args.configfile is not None and args.configfile.is_file():
        logger.info("Config override specified {}", args.configfile)
        config = from_config(args.configfile)
    config.verify_naming_config()
    target = args.file
    if args.dir is not None:
        target = args.dir
    if args.many is True:
        dir_with_sub_dirs_to_process(args.dir.absolute(), config, args.infos)
    else:
        command = determine_target_file(target.absolute(), config, inplace=True, nfo=args.infos)
        process_file(command)


if __name__ == "__main__":
    main(sys.argv[1:])
