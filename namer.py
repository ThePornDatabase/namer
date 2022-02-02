import os
from posixpath import basename
from typing import List, Tuple

from namer_types import NamerConfig, ComparisonResult, ProcessingResults, defaultConfig, fromConfig
from namer_dirscanner import find_largest_file_in_glob
from namer_file_parser import parse_file_name
from namer_mutagen import update_mp4_file
from namer_metadataapi import get_poster, match
import shutil
from pathlib import Path
import sys
import getopt
import logging

logger = logging.getLogger('namer')

def write_log_file(movie_file: str, match_attempts: List[ComparisonResult]) -> str:
    logname = os.path.splitext(movie_file)[0]+"_namer.log"
    logger.info("Writing log to {}".format(logname))
    f = open(logname, "wt")
    for attempt in match_attempts:
        f.write("\n")
        f.write("File                : {0}\n".format(attempt.name_parts.source_file_name))
        f.write("Scene Name          : {0}\n".format(attempt.looked_up.name))
        f.write("Match               : {0}\n".format(attempt.is_match()))
        f.write("Query URL           : {0}\n".format(attempt.looked_up.original_query))
        f.write("{0:5} Found Sitename: {1:50.50} Parsed Sitename: {2:50.50}\n".format(str(attempt.sitematch), attempt.looked_up.site, attempt.name_parts.site))  
        f.write("{0:5} Found Date    : {1:50.50} Parsed Date    : {2:50.50}\n".format(str(attempt.datematch), attempt.looked_up.date, attempt.name_parts.date))  
        f.write("{0:5} Found Name    : {1:50.50} Parsed Name    : {2:50.50}\n".format(attempt.name_match, attempt.name, attempt.name_parts.name))
    f.close()
    return logname


def determineFile(file_to_process: str, config: NamerConfig) -> Tuple[str, str]:
    dir = None
    file = None
    if os.path.isdir(file_to_process):
        print("Target dir: {}".format(file_to_process))
        dir = file_to_process
        file = find_largest_file_in_glob(file_to_process, "**/*.mp4", False)
        if file is None:
            file = find_largest_file_in_glob(file_to_process, "**/*.mkv", False)
    else:
        print("Target file: {}".format(file_to_process))
        relpath = os.path.relpath(file_to_process, config.watchdir)
        print("Relpath: {}".format(relpath))      
        dir = os.path.join(config.watchdir, Path(relpath).parts[0])
        file = file_to_process
    return (dir, file)


def setPermissions(file: str, config: NamerConfig):
    if os.path.isdir(file) and not config.set_dir_permissions is None:
        os.chmod(file, int(str(config.set_dir_permissions), 8))           
    elif config.set_file_permissions is not None:
        os.chmod(file, int(str(config.set_file_permissions), 8))
    if config.set_uid is not None and config.set_gid is not None: 
        os.chown(file, uid=config.set_uid, gid=config.set_gid)


def moveFiles(dir: str, file: str, config: NamerConfig ) -> Tuple[str, str]: 
    nameparts = os.path.splitext(os.path.basename(file))
    name = nameparts[0]
    ext = nameparts[1]
    if config.use_dir_name == True:
       name = os.path.basename(dir)
    target_dir = os.path.join(config.workingdir, name)
    if config.del_other_files:
       os.mkdir(target_dir, 0o775)
       setPermissions(target_dir, config)
       target_file = os.path.join(target_dir, name+ext)       
       os.rename(file, target_file)
       shutil.rmtree(path=dir, ignore_errors=True)
       return (target_dir, target_file)
    else:
       os.rename(file, os.path.join(dir, name+ext))
       os.rename(dir, target_dir)
       return (target_dir, os.path.join(target_dir, name+ext))       

def dirWithSubdirsToProcess(dirToScan: str, config: NamerConfig):
    if os.path.isdir(dirToScan):
        logger.info("Scanning dir {} for subdirs/files to process".format(dirToScan))
        for file in os.listdir(dirToScan):
            fullpath_file = os.path.join(dirToScan, file)
            if os.path.isdir(fullpath_file) or os.path.splitext(fullpath_file)[1].upper in ["MP4","MKV"]:
                process(fullpath_file, config)

def tagInPlace(video: str, config: NamerConfig, comparison_results: List[ComparisonResult]):
    if len(comparison_results) > 0 and comparison_results[0].is_match() == True:
        result = comparison_results[0]
        logfile = write_log_file(video, comparison_results)
        setPermissions(logfile, config)
        poster = None
        if config.enabled_tagging == True and os.path.splitext(video)[1].lower() == ".mp4":
            if config.enabled_poster == True:
                logger.info("Downloading poster: {}".format(result.looked_up.poster_url))
                poster = get_poster(result.looked_up.poster_url, config.porndb_token, video)
                setPermissions(poster, config)
            logger.info("Updating file metadata (atoms): {}".format(video))
            update_mp4_file(video, result.looked_up, poster, config)            
        logger.info("Done tagging file: {}".format(video))
        if poster != None:
            os.remove(poster)


def process(file_to_process: str, config: NamerConfig) -> ProcessingResults:
    logger.info("Analyzing: {}".format(file_to_process))
    dir = None
    if os.path.isdir(file_to_process):
        logger.info("Target dir: {}".format(file_to_process))
        dir = file_to_process
        file = find_largest_file_in_glob(file_to_process, "**/*.mp4")
        if file is None:
            file = find_largest_file_in_glob(file_to_process, "**/*.mkv")
    else:
        file = file_to_process

    if config.prefer_dir_name_if_available and dir != None:
        name = os.path.basename(dir)+os.path.splitext(file)[1]
    else:
        name = os.path.basename(file)

    output = ProcessingResults()
    output.dirfile = dir
    output.video_file = file
    output.final_name_relative=os.path.relpath(file, dir)

    if dir == None:
        dir = os.path.dirname(file)

    if dir != None and file != None:
        #remove sample files
        logger.info("Processing: {}".format(name))
        file_name_parts = parse_file_name(name)
        comparison_results = match(file_name_parts, config.porndb_token)
        logfile = write_log_file(file, comparison_results)
        setPermissions(logfile, config)
        output.namer_log_file=logfile
        if len(comparison_results) > 0 and comparison_results[0].is_match() == True:
            result = comparison_results[0]
            output.found = True
            output.final_name_relative = result.looked_up.new_file_name(config.new_relative_path_name)
            finalfile = os.path.join(dir, result.looked_up.new_file_name(config.inplace_name))
            os.rename(file, finalfile)
            setPermissions(finalfile, config)
            tagInPlace(finalfile, config, comparison_results)
            logger.info("Done processing file: {}".format(file_to_process))
        else:
            output.final_name_relative=os.path.relpath(file, dir)
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
    logger_level = logging.DEBUG
    try:
        opts, args = getopt.getopt(argv,"hc:f:d:m",["help","configfile=","file=","dir=","many"])
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
    if  config_overide != None:
        if os.path.isfile(config_overide):
            logger.info("Config override specified, but file does not exit: {}".format(config_overide))
            usage()
            sys.exit(2)
        else:
            config = fromConfig(config_overide)
    if file_to_process != None and dir_to_process != None:
        print("set -f or -d, but not both.")
        sys.exit(2)
    elif (file_to_process != None or dir_to_process != None) and not many == True:
        target = file_to_process
        if dir_to_process != None:
            target = dir_to_process
        if target == None:
            print("set target file or directory, -f or -d")
            sys.exit(2)    
        process(target, config)
    elif dir_to_process != None and many == True:
        dirWithSubdirsToProcess(dir_to_process, config)
    else:    
        usage()
        sys.exit(2)  


if __name__ == "__main__":
    main(sys.argv[1:])
    sys.exit(0) 

