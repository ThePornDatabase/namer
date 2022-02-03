import os
import shutil
from pathlib import Path
import sys
import getopt
import logging
from typing import List, Tuple
from namer_types import NamerConfig, ComparisonResult, ProcessingResults, defaultConfig, fromConfig
from namer_dirscanner import find_largest_file_in_glob
from namer_file_parser import parse_file_name
from namer_mutagen import update_mp4_file
from namer_metadataapi import get_poster, match

logger = logging.getLogger('namer')

def write_log_file(movie_file: str, match_attempts: List[ComparisonResult]) -> str:
    logname = os.path.splitext(movie_file)[0]+"_namer.log"
    logger.info("Writing log to %s",logname)
    with open(logname, "wt", encoding='utf-8') as log_file:
        for attempt in match_attempts:
            log_file.write("\n")
            log_file.write(f"File                : {attempt.name_parts.source_file_name}\n")
            log_file.write(f"Scene Name          : {attempt.looked_up.name}\n")
            log_file.write(f"Match               : {attempt.is_match()}\n")
            log_file.write(f"Query URL           : {attempt.looked_up.original_query}\n")
            log_file.write(f"{str(attempt.sitematch):5} Found Sitename: {attempt.looked_up.site:50.50} Parsed Sitename: {attempt.name_parts.site:50.50}\n")
            log_file.write(f"{str(attempt.datematch):5} Found Date    : {attempt.looked_up.date:50.50} Parsed Date    : {attempt.name_parts.date:50.50}\n")
            log_file.write(f"{attempt.name_match:5} Found Name    : {attempt.name:50.50} Parsed Name    : {attempt.name_parts.name:50.50}\n")
    return logname


def determineFile(file_to_process: str, config: NamerConfig) -> Tuple[str, str]:
    containing_dir = None
    file = None
    if os.path.isdir(file_to_process):
        logger.info("Target dir: %s",file_to_process)
        containing_dir = file_to_process
        file = find_largest_file_in_glob(file_to_process, "**/*.mp4")
        if file is None:
            file = find_largest_file_in_glob(file_to_process, "**/*.mkv")
    else:
        logger.info("Target file: %s",file_to_process)
        relpath = os.path.relpath(file_to_process, config.watchdir)
        logger.info("Relpath: %s",relpath)
        containing_dir = os.path.join(config.watchdir, Path(relpath).parts[0])
        file = file_to_process
    return (containing_dir, file)


def setPermissions(file: str, config: NamerConfig):
    if os.path.isdir(file) and not config.set_dir_permissions is None:
        os.chmod(file, int(str(config.set_dir_permissions), 8))           
    elif config.set_file_permissions is not None:
        os.chmod(file, int(str(config.set_file_permissions), 8))
    if config.set_uid is not None and config.set_gid is not None: 
        os.chown(file, uid=config.set_uid, gid=config.set_gid)


def moveFiles(containing_dir: str, file: str, config: NamerConfig) -> Tuple[str, str]:
    nameparts = os.path.splitext(os.path.basename(file))
    name = nameparts[0]
    ext = nameparts[1]
    if config.use_dir_name is True:
        name = os.path.basename(containing_dir)
    target_dir = os.path.join(config.workingdir, name)
    if config.del_other_files:
        os.mkdir(target_dir, 0o775)
        setPermissions(target_dir, config)
        target_file = os.path.join(target_dir, name+ext)
        os.rename(file, target_file)
        shutil.rmtree(path=containing_dir, ignore_errors=True)
        return (target_dir, target_file)
    os.rename(file, os.path.join(containing_dir, name+ext))
    os.rename(containing_dir, target_dir)
    return (target_dir, os.path.join(target_dir, name+ext))

def dirWithSubdirsToProcess(dir_to_scan: str, config: NamerConfig):
    if os.path.isdir(dir_to_scan):
        logger.info("Scanning dir %s for subdirs/files to process",dir_to_scan)
        for file in os.listdir(dir_to_scan):
            fullpath_file = os.path.join(dir_to_scan, file)
            if os.path.isdir(fullpath_file) or os.path.splitext(fullpath_file)[1].upper in ["MP4","MKV"]:
                process(fullpath_file, config)

def tagInPlace(video: str, config: NamerConfig, comparison_results: List[ComparisonResult]):
    if len(comparison_results) > 0 and comparison_results[0].is_match() == True:
        result = comparison_results[0]
        logfile = write_log_file(video, comparison_results)
        setPermissions(logfile, config)
        poster = None
        if config.enabled_tagging is True and os.path.splitext(video)[1].lower() == ".mp4":
            if config.enabled_poster is True:
                logger.info("Downloading poster: %s",result.looked_up.poster_url)
                poster = get_poster(result.looked_up.poster_url, config.porndb_token, video)
                setPermissions(poster, config)
            logger.info("Updating file metadata (atoms): %s",video)
            update_mp4_file(video, result.looked_up, poster, config)
        logger.info("Done tagging file: %s",video)
        if poster is not None:
            os.remove(poster)


def process(file_to_process: str, config: NamerConfig) -> ProcessingResults:
    logger.info("Analyzing: %s",file_to_process)
    containing_dir = None
    if os.path.isdir(file_to_process):
        logger.info("Target dir: %s",file_to_process)
        containing_dir = file_to_process
        file = find_largest_file_in_glob(file_to_process, "**/*.mp4")
        if file is None:
            file = find_largest_file_in_glob(file_to_process, "**/*.mkv")
    else:
        file = file_to_process

    if config.prefer_dir_name_if_available and containing_dir is not None:
        name = os.path.basename(containing_dir)+os.path.splitext(file)[1]
    else:
        name = os.path.basename(file)

    output = ProcessingResults()
    output.dirfile = containing_dir
    output.video_file = file
    output.final_name_relative=os.path.relpath(file, containing_dir)

    if containing_dir is None:
        containing_dir = os.path.dirname(file)

    if containing_dir is not None and file is not None:
        #remove sample files
        logger.info("Processing: %s",name)
        file_name_parts = parse_file_name(name)
        comparison_results = match(file_name_parts, config.porndb_token)
        logfile = write_log_file(file, comparison_results)
        setPermissions(logfile, config)
        output.namer_log_file=logfile
        if len(comparison_results) > 0 and comparison_results[0].is_match() is True:
            result = comparison_results[0]
            output.found = True
            output.final_name_relative = result.looked_up.new_file_name(config.new_relative_path_name)
            output.video_file = os.path.join(containing_dir, result.looked_up.new_file_name(config.inplace_name))
            os.rename(file, output.video_file)
            setPermissions(output.video_file, config)
            tagInPlace(output.video_file, config, comparison_results)
            logger.info("Done processing file: %s, moved to %s", file_to_process,output.video_file)
        else:
            output.final_name_relative=os.path.relpath(file, containing_dir)
    return output

def usage():
    print("-h, --help  : this message.")
    print("-c, --config: config file, defaults first to env var NAMER_CONFIG, then local path namer.cfg, and finally ~/.namer.cfg.")
    print("-f, --file  : a single file to process, and rename.")
    print("-d, --dif   : a directory to process.")
    print("-m, --many  : if set, a directory have all it's sub directories processed. Files move only within sub dirs, or are renamed in place, if in the root dir to scan")

def main(argv):
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
            config_overide = arg
        elif opt in ("-f", "--file"):
            file_to_process = arg
        elif opt in ("-d", "--dir"):
            dir_to_process = arg
        elif opt in ("-m", "--many"):
            many = True
    config = defaultConfig()
    logging.basicConfig(level=logger_level)
    if  config_overide is not None:
        if os.path.isfile(config_overide):
            logger.info("Config override specified, but file does not exit: %s",config_overide)
            usage()
            sys.exit(2)
        else:
            config = fromConfig(config_overide)
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
        dirWithSubdirsToProcess(dir_to_process, config)
    else:
        usage()
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
    sys.exit(0) 

