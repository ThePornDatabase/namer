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

from numpy import sort
from namer_types import NamerConfig, ComparisonResult, ProcessingResults, default_config, from_config
from namer_dirscanner import find_largest_file_in_glob
from namer_file_parser import parse_file_name
from namer_mutagen import update_mp4_file
from namer_metadataapi import get_poster, match

logger = logging.getLogger('namer')

def write_log_file(movie_file: str, match_attempts: List[ComparisonResult]) -> str:
    """
    Given porndb scene results sorted by how closely they match a file,  write the contents
    of the result matches to a log file.
    """
    logname = os.path.splitext(movie_file)[0]+"_namer.log"
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

def set_permissions(file: str, config: NamerConfig):
    """
    Given a file or dir, set permissions from NamerConfig.set_file_permissions,
    NamerConfig.set_dir_permissions, and uid/gid if set for the current process.
    """
    if hasattr(os, "chmod"):
        if os.path.isdir(file) and not config.set_dir_permissions is None:
            os.chmod(file, int(str(config.set_dir_permissions), 8))
        elif config.set_file_permissions is not None:
            os.chmod(file, int(str(config.set_file_permissions), 8))
        if config.set_uid is not None and config.set_gid is not None:
            os.chown(file, uid=config.set_uid, gid=config.set_gid)

def dir_with_subdirs_to_process(dir_to_scan: Path, config: NamerConfig):
    """
    Used to find subdirs of a directory to be individually processed.
    The directories will be scanned for media and named/tagged in place
    based on config settings.
    """
    if dir_to_scan is not None and dir_to_scan.is_dir():
        logger.info("Scanning dir %s for subdirs/files to process",dir_to_scan)
        files = [f for f in dir_to_scan.iterdir()]
        files.sort()
        for file in files:
            fullpath_file = dir_to_scan / file
            if fullpath_file.is_dir() or fullpath_file.suffix.upper() in [".MP4",".MKV"]:
                process(fullpath_file, config)

def tag_in_place(video: Path, config: NamerConfig, comparison_results: List[ComparisonResult]):
    """
    Uses ComparisonResults to update an mp4 file's metadata based on a match in
    ComparisonResults.   Expects the first item of list to be the match if there is one.
    Will download a poster as well depending on NamerConfig config setting.
    """
    if len(comparison_results) > 0 and comparison_results[0].is_match() is True:
        result = comparison_results[0]
        logfile = write_log_file(video, comparison_results)
        set_permissions(logfile, config)
        poster = None
        if config.enabled_tagging is True and video.suffix.lower() == ".mp4":
            if config.enabled_poster is True:
                logger.info("Downloading poster: %s",result.looked_up.poster_url)
                poster = get_poster(result.looked_up.poster_url, config.porndb_token, video)
                set_permissions(poster, config)
            logger.info("Updating file metadata (atoms): %s",video)
            update_mp4_file(video, result.looked_up, poster, config)
        logger.info("Done tagging file: %s",video)
        if poster is not None:
            os.remove(poster)


def process(file_to_process: Path, config: NamerConfig) -> ProcessingResults:
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

    output = ProcessingResults()
    output.dirfile = containing_dir
    output.video_file = file

    if containing_dir is None:
        containing_dir = file.parent


    logger.info("file: %s",file)
    logger.info("dir : %s",containing_dir)


    output.final_name_relative=os.path.relpath(file, containing_dir)

    if containing_dir is not None and file is not None:
        #remove sample files
        logger.info("Processing: %s",name)
        file_name_parts = parse_file_name(name)
        if file_name_parts is not None:
            comparison_results = match(file_name_parts, config.porndb_token)
            logfile = write_log_file(file, comparison_results)
            set_permissions(logfile, config)
            output.namer_log_file=logfile
            if len(comparison_results) > 0 and comparison_results[0].is_match() is True:
                result = comparison_results[0]
                output.found = True
                output.final_name_relative = result.looked_up.new_file_name(config.new_relative_path_name)
                output.video_file = containing_dir / result.looked_up.new_file_name(config.inplace_name)
                file.rename(output.video_file.resolve())
                set_permissions(output.video_file.resolve(), config)
                tag_in_place(output.video_file.resolve(), config, comparison_results)
                logger.info("Done processing file: %s, moved to %s", file_to_process,output.video_file)
            else:
                output.final_name_relative=os.path.relpath(file, containing_dir)
        else:
            logger.warning("Could not parse file/dir for name to look up: %s", name)
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

def get_opts(argv) -> Tuple[int, Path, Path, Path, bool]:
    """
    Read command line args are return them as a tuple.
    """
    config_overide = None
    file_to_process = None
    dir_to_process = None
    many = False
    logger_level = logging.INFO
    try:
        opts, __args = getopt.getopt(argv,"hc:f:d:m",["help","configfile=","file=","dir=","many"])
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
    return (logger_level, config_overide, file_to_process, dir_to_process, many)

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

    logger_level, config_overide, file_to_process, dir_to_process, many = get_opts(argv)

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
        process(target, config)
    elif dir_to_process is not None and many is True:
        dir_with_subdirs_to_process(dir_to_process, config)
    else:
        usage()
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
    sys.exit(0)
