"""
This file can process individual movie files in place.
There name, or directory name, will be analyzed, matched against
the porndb, and used for renaming (in place), and updating an mp4
file's metadata (poster, artists, etc.)
"""
import os
from pathlib import Path
import sys
import getopt
import logging
from typing import List, Tuple
from namer_moviexml import parse_movie_xml_file

from namer_types import LookedUpFileInfo, NamerConfig, ComparisonResult, ProcessingResults, default_config, from_config
from namer_dirscanner import find_largest_file_in_glob
from namer_file_parser import parse_file_name
from namer_mutagen import update_mp4_file
from namer_metadataapi import get_poster, match

logger = logging.getLogger('namer')

def write_log_file(movie_file: Path, match_attempts: List[ComparisonResult]) -> str:
    """
    Given porndb scene results sorted by how closely they match a file,  write the contents
    of the result matches to a log file.
    """
    logname = movie_file.with_name(movie_file.stem+"_namer.log")
    logger.info("Writing log to %s",logname)
    with open(logname, "wt", encoding='utf-8') as log_file:
        for attempt in match_attempts:
            log_file.write("\n")
            log_file.write(f"File                : {attempt.name_parts.source_file_name}\n")
            log_file.write(f"Scene Name          : {attempt.looked_up.name}\n")
            log_file.write(f"Match               : {attempt.is_match()}\n")
            log_file.write(f"Query URL           : {attempt.looked_up.original_query}\n")
            log_file.write(f"{str(attempt.sitematch):5} Found Sitename: {attempt.looked_up.site:50.50} Parsed Sitename:"+
                f" {attempt.name_parts.site:50.50}\n")
            log_file.write(f"{str(attempt.datematch):5} Found Date    : {attempt.looked_up.date:50.50} Parsed Date    :"+
                f" {attempt.name_parts.date:50.50}\n")
            log_file.write(f"{attempt.name_match:5.1f} Found Name    : {attempt.name:50.50} Parsed Name    :"+
                f" {attempt.name_parts.name:50.50}\n")
    return logname

def set_permissions(file: Path, config: NamerConfig):
    """
    Given a file or dir, set permissions from NamerConfig.set_file_permissions,
    NamerConfig.set_dir_permissions, and uid/gid if set for the current process.
    """
    if hasattr(os, "chmod"):
        if file.is_dir() and not config.set_dir_permissions is None:
            file.chmod(int(str(config.set_dir_permissions), 8))
        elif config.set_file_permissions is not None:
            file.chmod(int(str(config.set_file_permissions), 8))
        if config.set_uid is not None and config.set_gid is not None:
            os.chown(file, uid=config.set_uid, gid=config.set_gid)

def dir_with_subdirs_to_process(dir_to_scan: Path, config: NamerConfig, infos: bool = False):
    """
    Used to find subdirs of a directory to be individually processed.
    The directories will be scanned for media and named/tagged in place
    based on config settings.
    """
    if dir_to_scan is not None and dir_to_scan.is_dir():
        logger.info("Scanning dir %s for subdirs/files to process",dir_to_scan)
        files = list(dir_to_scan.iterdir())
        files.sort()
        for file in files:
            fullpath_file = dir_to_scan / file
            if fullpath_file.is_dir() or fullpath_file.suffix.upper() in [".MP4",".MKV"]:
                process(fullpath_file, config, infos)

def tag_in_place(video: Path, config: NamerConfig, new_metadata: LookedUpFileInfo):
    """
    Uses ComparisonResults to update an mp4 file's metadata based on a match in
    ComparisonResults.   Expects the first item of list to be the match if there is one.
    Will download a poster as well depending on NamerConfig config setting.
    """
    if new_metadata is not None:
        poster = None
        if config.enabled_tagging is True and video.suffix.lower() == ".mp4":
            if config.enabled_poster is True:
                logger.info("Downloading poster: %s",new_metadata.poster_url)
                poster = get_poster(new_metadata.poster_url, config.porndb_token, video)
                set_permissions(poster, config)
            logger.info("Updating file metadata (atoms): %s",video)
            update_mp4_file(video, new_metadata, poster, config)
        logger.info("Done tagging file: %s",video)
        if poster is not None:
            poster.unlink()

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
        logger.info("Target dir: %s",file_to_process)
        containing_dir = file_to_process
        file = find_largest_file_in_glob(file_to_process, "**/*.mp4")
        if file is None:
            file = find_largest_file_in_glob(file_to_process, "**/*.mkv")
    else:
        file = file_to_process

    if config.prefer_dir_name_if_available and containing_dir is not None:
        name = containing_dir.stem+file.suffix
    else:
        name = file.name

    logger.info("file: %s",file)
    logger.info("dir : %s",containing_dir)

    results.dirfile = containing_dir
    results.video_file = file
    results.parsed_file = parse_file_name(name)
    if containing_dir is True:
        results.final_name_relative = file.relative_to(containing_dir)
    else:
        results.final_name_relative = file.parent
    return results

def get_local_metadata_if_requested(video_file: Path) -> LookedUpFileInfo:
    """
    If there is an .nfo file next to the video_file, attempt to read it as
    a Emby/Jellyfin style movie xml file.
    """
    nfo_file = video_file.parent / (video_file.stem + ".nfo")
    if nfo_file.is_file() and nfo_file.exists():
        return parse_movie_xml_file(nfo_file)
    return None

def process(file_to_process: Path, config: NamerConfig, infos: bool = False) -> ProcessingResults:
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
    logger.info("Analyzing: %s",file_to_process)
    output: ProcessingResults = determine_target_file(file_to_process, config)
    if output.video_file is not None:
        logger.info("Processing: %s", output.video_file)
        # Match to nfo files, if enabled and found.
        if infos is True:
            output.new_metadata = get_local_metadata_if_requested(output.video_file)
            output.new_metadata.original_parsed_filename = output.parsed_file
        if output.new_metadata is None:
            output.search_results = match(output.parsed_file, config.porndb_token)
            if len(output.search_results) > 0 and output.search_results[0].is_match() is True:
                output.new_metadata = output.search_results[0].looked_up
        target_dir = output.dirfile if output.dirfile is not None else output.video_file.parent
        if output.new_metadata is not None:
            newname = target_dir / output.new_metadata.new_file_name(config.inplace_name)
            output.video_file.rename(newname.resolve())
            output.video_file = newname.resolve()
            output.final_name_relative = output.new_metadata.new_file_name(config.new_relative_path_name)
            set_permissions(output.video_file, config)
            tag_in_place(output.video_file, config, output.new_metadata)
            logger.info("Done processing file: %s, moved to %s", file_to_process,output.video_file)
        else:
            #not matched.
            output.final_name_relative=os.path.relpath(output.video_file, target_dir)

        # Write log file if needed.
        if config.write_namer_log is True and output.search_results is not None:
            logfile = write_log_file(output.video_file, output.search_results)
            set_permissions(logfile, config)
            output.namer_log_file=logfile
    return output

def usage():
    """
    Displays usage info for the main method of this file which will rename a
    file in it's current directory, and optionally update it's metadata tags as well.
    """
    print("-h, --help  : this message.")
    print("-c, --config: config file, defaults first to env var NAMER_CONFIG,"
        +" then local path namer.cfg, and finally ~/.namer.cfg.")
    print("-f, --file  : a single file to process, and rename.")
    print("-d, --dif   : a directory to process.")
    print("-m, --many  : if set, a directory have all it's sub directories processed."+
        " Files move only within sub dirs, or are renamed in place, if in the root dir to scan")
    print("-i, --infos  : if set, .nfo files will attempt to be accessed next to movie files" +
        ", if info files are found and parsed success, that metadata will be used rather than " +
        "porndb matching.  If using jellyfin .nfo files, please bump your release date by one day "+
        "until they fix this issue: https://github.com/jellyfin/jellyfin/issues/7271.")


def get_opts(argv) -> Tuple[int, Path, Path, Path, bool, bool]:
    """
    Read command line args are return them as a tuple.
    """
    config_overide = None
    file_to_process = None
    dir_to_process = None
    many = False
    infos = False
    logger_level = logging.INFO
    try:
        opts, __args = getopt.getopt(argv,"hc:f:d:mi",["help","configfile=","file=","dir=","many","infos"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            usage()
            sys.exit()
        elif opt == '-q':
            logger_level=logging.ERROR
        elif opt in ("-c", "--configfile"):
            config_overide = Path(arg)
        elif opt in ("-f", "--file"):
            file_to_process = Path(arg)
        elif opt in ("-d", "--dir"):
            dir_to_process = Path(arg)
        elif opt in ("-m", "--many"):
            many = True
        elif opt in ("-i", "--infos"):
            infos = True
    return (logger_level, config_overide, file_to_process, dir_to_process, many, infos)

def check_arguments(file_to_process: Path, dir_to_process: Path, config_overide: Path):
    """
    check arguments.
    """
    error = False
    if file_to_process is not None:
        logger.info("File to process: %s", file_to_process)
        if not file_to_process.is_file():
            logger.error("Error not a file! %s", file_to_process)
            error = True

    if dir_to_process is not None:
        logger.info("Directory to process: %s",dir_to_process)
        if not dir_to_process.is_dir():
            logger.info("Error not a directory! %s", dir_to_process)
            error = True

    if config_overide is not None:
        logger.info("Config override specified: %s",config_overide)
        if not config_overide.is_file():
            logger.info("Config override specified, but file does not exit: %s",config_overide)
            error = True

    if error:
        usage()
        sys.exit(2)



def main(argv):
    """
    Used to tag and rename files from the command line.
    See usage function above.
    """

    logger_level, config_overide, file_to_process, dir_to_process, many, infos = get_opts(argv)

    check_arguments(file_to_process, dir_to_process, config_overide)

    config = default_config()
    logging.basicConfig(level=logger_level)
    if config_overide is not None and config_overide.is_file:
        logger.info("Config override specified %s",config_overide)
        config = from_config(config_overide)
    config.verify_config()
    if file_to_process is not None and dir_to_process is not None:
        print("set -f or -d, but not both.")
        sys.exit(2)
    elif (file_to_process is not None or dir_to_process is not None) and many is False:
        target = file_to_process
        if dir_to_process is not None:
            target = dir_to_process
        if target is None:
            print("set target file or directory, -f or -d")
            sys.exit(2)
        process(target, config, infos)
    elif dir_to_process is not None and many is True:
        dir_with_subdirs_to_process(dir_to_process, config, infos)
    else:
        usage()
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
    sys.exit(0)
