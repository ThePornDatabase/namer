"""
Responsible for finding the larges file with an extension in a directory
"""
from pathlib import Path
from typing import List, Tuple
import unittest
import logging
from namer_file_parser import parse_file_name

logger = logging.getLogger('ffmpeg')

def find_largest_file_in_glob(rootdir: Path, globstr: str) -> Path:
    """
    returns largest matching file
    """
    list_of_files = list(rootdir.rglob(globstr))
    logger.info("found files %s", list_of_files)
    file = None
    if len(list_of_files) > 0:
        file = max( list_of_files, key =  lambda x: x.stat().st_size)
    return file

def find_targets_for_naming(rootdir: Path) -> List[Tuple[str, str]]:
    """
    Scans a directory to find targets for identification, renaming and tagging.
    assuming that if a folder exists, it is the source of the name, and that the single largest
    mp4 file in dir is the target for inclusion in a library.
    If an mp4 file exists in the root dir, it will be assumed that the mp4 file name is the to be
    used for identifaction, and the file should be processed on it's own.
    """
    to_process: List[(str, str, str)] = []
    files = list(Path(rootdir).iterdir())
    files.sort()
    for file_name in files:
        target_file = rootdir / file_name
        if  target_file.is_dir():
            name_parts = parse_file_name(str(target_file) + ".mp4")
            if name_parts is not None:
                max_mp4_file = find_largest_file_in_glob(target_file,"**/*.mp4")
                if max_mp4_file is not None:
                    to_process.append((target_file,max_mp4_file))
        if target_file.is_file() and target_file.suffix.lower() in [".mp4"]:
            to_process.append((None,target_file))
    return to_process

if __name__ == '__main__':
    unittest.main()
        