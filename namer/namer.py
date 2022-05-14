"""
This file can process individual movie files in place.
There name, or directory name, will be analyzed, matched against
the porndb, and used for renaming (in place), and updating an mp4
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
from namer.metadataapi import get_image, get_trailer, match
from namer.moviexml import parse_movie_xml_file, write_nfo
from namer.mutagen import update_mp4_file
from namer.types import default_config, from_config, LookedUpFileInfo, NamerConfig, ProcessingResults, set_permissions, write_log_file

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


def dir_with_subdirs_to_process(dir_to_scan: Path, config: NamerConfig, infos: bool = False):
    """
    Used to find subdirs of a directory to be individually processed.
    The directories will be scanned for media and named/tagged in place
    based on config settings.
    """
    if dir_to_scan is not None and dir_to_scan.is_dir() and dir_to_scan.exists():
        logger.info("Scanning dir {} for subdirs/files to process", dir_to_scan)
        files = list(dir_to_scan.iterdir())
        files.sort()
        for file in files:
            fullpath_file = dir_to_scan / file
            if fullpath_file.is_dir() or fullpath_file.suffix.upper() in [".MP4", ".MKV"]:
                process(fullpath_file, config, infos)


def tag_in_place(video: Optional[Path], config: NamerConfig, new_metadata: LookedUpFileInfo):
    """
    Uses ComparisonResults to update an mp4 file's metadata based on a match in
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


def find_target_file(rootdir: Path, config: NamerConfig) -> Path:
    """
    returns largest matching file
    """
    list_of_files = list(rootdir.rglob("**/*.*"))
    file = None
    if len(list_of_files) > 0:
        for target_ext in config.target_extensions:
            filtered = list(filter(lambda o, ext=target_ext: o.suffix is not None and o.suffix.lower()[1:] == ext, list_of_files))
            if file is None and filtered is not None and len(filtered) > 0:
                file = max(filtered, key=lambda x: x.stat().st_size)
    return file


def determine_target_file(file_to_process: Path, config: NamerConfig) -> ProcessingResults:
    """
    Base on the file to process - which may be a file or a dir, and configuration, determine
    the file if needed (largest mp4, or mkv in a directory), or the directory (parent dir of file),
    as well as determine which should be used for attempted naming.

    If config.prefer_dir_name_if_available is set to True and a directory was passed as file_to_process
    then the dirctory's name will be returned as name, else the found file's name is used.
    """
    results = ProcessingResults()

    containing_dir = None
    if file_to_process.is_dir():
        logger.info("Target dir: {}", file_to_process)
        containing_dir = file_to_process
        results.dirfile = containing_dir
        results.video_file = find_target_file(file_to_process, config)
    else:
        results.video_file = file_to_process

    if config.prefer_dir_name_if_available and containing_dir is not None:
        name = containing_dir.name + results.video_file.suffix
    else:
        name = results.video_file.name

    logger.info("file: {}", results.video_file)
    logger.info("dir : {}", containing_dir)

    results.parsed_file = parse_file_name(name, config.name_parser)
    if containing_dir is True:
        results.final_name_relative = results.video_file.relative_to(containing_dir)
    else:
        results.final_name_relative = results.video_file.parent
    return results


def get_local_metadata_if_requested(video_file: Path) -> Optional[LookedUpFileInfo]:
    """
    If there is an .nfo file next to the video_file, attempt to read it as
    a Emby/Jellyfin style movie xml file.
    """
    nfo_file = video_file.parent / (video_file.stem + ".nfo")
    if nfo_file.is_file() and nfo_file.exists():
        return parse_movie_xml_file(nfo_file)
    return None


def move_to_final_location(to_move: Optional[Path],
                           target_dir: Path,
                           template: str,
                           new_metadata: LookedUpFileInfo,
                           config: NamerConfig) -> Optional[Path]:
    """
    Moves a file or directory to it's final location after verifying there is no collision.
    Should a collision occur, the file is appropriately renamed to avoid collision.
    """
    infix = 0
    newname = None
    if to_move is not None:
        while True:
            relative_path = Path(new_metadata.new_file_name(template, f"({infix})"))
            newname = target_dir / relative_path
            newname = newname.resolve()
            infix += 1
            if not newname.exists() or to_move.samefile(newname):
                break
        newname.parent.mkdir(exist_ok=True, parents=True)
        set_permissions(target_dir / relative_path.parts[0], config)
        to_move.rename(newname)
        set_permissions(newname, config)
    return newname


def process_file(file_to_process: Path, config: NamerConfig, infos: bool = False) -> ProcessingResults:
    """
    Bread and butter method.
    Given a file, determines if it's a dir, if so, the dir name may be used
    for comparison with the porndb.   The larges mp4/mkv file in the directory
    or any subdirectories will be assumed to be the movie file.

    Does not properly handle multi-part movies.

    If the input file is not a dir it's name will be used and it is assumed to
    be the movie file we wish to tag.

    The movie is either renamed in place if a file, or renamed and move to the root
    of the dir if a dir was passed in.

    The file is then update based on the metadata from the porndb if an mp4.
    """
    logger.info("Analyzing: {}", file_to_process)
    output: ProcessingResults = determine_target_file(file_to_process, config)
    if output.video_file is not None:
        logger.info("Processing: {}", output.video_file)
        # Match to nfo files, if enabled and found.
        if infos is True:
            output.new_metadata = get_local_metadata_if_requested(output.video_file)
            if output.new_metadata is not None:
                output.new_metadata.original_parsed_filename = output.parsed_file
        if output.new_metadata is None and output.parsed_file is not None and output.parsed_file.name is not None:
            output.search_results = match(output.parsed_file, config)
            if len(output.search_results) > 0 and output.search_results[0].is_match() is True:
                output.new_metadata = output.search_results[0].looked_up
        else:
            if not infos:
                if file_to_process != output.video_file:
                    logger.error("""
                        Could not process file in directory: {}
                        Likely attempted to use the directory's name as the name to parse.
                        In general the dir or file's name should start with a site, a date and end with an extension
                        Target video file in dir was: {}""", file_to_process, output.video_file)
                else:
                    logger.error("""
                        Could not process files: {}
                        In the file's name should start with a site, a date and end with an extension""", file_to_process)
        target_dir = output.dirfile if output.dirfile is not None else output.video_file.parent
        set_permissions(target_dir, config)
        if output.new_metadata is not None:
            output.video_file = move_to_final_location(
                to_move=output.video_file,
                target_dir=output.video_file.parent,
                template=config.inplace_name,
                new_metadata=output.new_metadata,
                config=config,
            )
            tag_in_place(output.video_file, config, output.new_metadata)
            logger.info("Done processing file: {}, moved to {}", file_to_process, output.video_file)
    return output


def process(file_to_process: Path, config: NamerConfig, infos: bool = False) -> ProcessingResults:
    """
    Fully process (match, tag, rename) a single file in place and download any extra artifacts requested.
    trailer, .nfo file, logs.
    """
    results = process_file(file_to_process, config, infos)
    add_extra_artifacts(results, config)
    return results


def add_extra_artifacts(results: ProcessingResults, config: NamerConfig):
    """
    Once the file is in it's final location we will grab other relevant output if requested.
    """
    trailer = None
    if config.write_namer_log is True:
        write_log_file(results.video_file, results.search_results, config)
    if config.trailer_location is not None and not len(config.trailer_location) == 0 and results.new_metadata is not None:
        trailer = get_trailer(results.new_metadata.trailer_url, results.video_file, config)
    if config.write_nfo and results.new_metadata is not None:
        poster = get_image(results.new_metadata.poster_url, "-poster", results.video_file, config)
        background = get_image(results.new_metadata.background_url, "-background", results.video_file, config)
        for performer in results.new_metadata.performers:
            poster = get_image(performer.image, performer.name.replace(" ", "-") + "-image", results.video_file, config)
            if poster is not None:
                performer.image = str(poster)
        write_nfo(results, config, trailer, poster, background)


def check_arguments(file_to_process: Path, dir_to_process: Path, config_overide: Path):
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

    if config_overide is not None:
        logger.info("Config override specified: {}", config_overide)
        if not config_overide.is_file() or not config_overide.exists():
            logger.info("Config override specified, but file does not exit: {}", config_overide)
            error = True
    return error


def main(arglist: List[str]):
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
    args = parser.parse_args(arglist)
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
        dir_with_subdirs_to_process(args.dir.absolute(), config, args.infos)
    else:
        process(target.absolute(), config, args.infos)


if __name__ == "__main__":
    main(sys.argv[1:])
