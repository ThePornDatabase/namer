import os
import json
import glob
from typing import List, Tuple
import urllib.request
import urllib.parse
import unittest
import tempfile
from namer_types import FileNameParts, LookedUpFileInfo, Performer
from namer_file_parser import parse_file_name
from namer_metadataapi import get_response_json_object, metadataapi_response_to_data, buildUrl, getMetadataApiNetFileInfo
from distutils.dir_util import copy_tree
from types import SimpleNamespace
from dataclasses import dataclass
import re
from rapidfuzz import process

def find_largest_file_in_glob(dir: str,globstr: str, remove_other: bool = False) -> str:
    """
    returns largest matching file
    """
    list_of_files = glob.glob(pathname=os.path.join(dir,globstr), recursive=True)
    print("found files".format(list_of_files))
    file = None
    if (len(list_of_files) > 0):
        file = max( list_of_files, key =  lambda x: os.stat(x).st_size)
        if remove_other == True:
            for to_rm_file in list_of_files[1:]:
                print("removing file: {}".format(to_rm_file))
                os.remove(to_rm_file)
    return file

def find_targets_for_naming(rootdir: str) -> List[Tuple[str, str]]:
    """
    Scans a directory to find targets for identification, renaming and tagging.
    assuming that if a folder exists, it is the source of the name, and that the single largest
    mp4 file in dir is the target for inclusion in a library.
    If an mp4 file exists in the root dir, it will be assumed that the mp4 file name is the to be 
    used for identifaction, and the file should be processed on it's own.    
    """
    to_process: List[(str, str, str)] = []
    for file in os.listdir(rootdir):
        file = os.path.join(rootdir, file)
        if os.path.isdir(file):
            name_parts = parse_file_name(file + ".mp4")
            if name_parts != None:
                max_mp4_file = find_largest_file_in_glob(file,"**/*.mp4")
                if max_mp4_file != None:
                    to_process.append((file,max_mp4_file))
        if os.path.isfile(file) and file.endswith(".mp4"):
            to_process.append((None,file))
    return to_process        

class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    current=os.path.dirname(os.path.abspath(__file__))

    def prepare_workdir():
        current=os.path.dirname(os.path.abspath(__file__))
        test_fixture="test"
        tmpdir = tempfile.TemporaryDirectory()
        test_root = os.path.join(tmpdir.name,test_fixture)
        copy_tree(os.path.join(current, test_fixture), tmpdir.name)
        return tmpdir


    def test_find_largest_file_in_glob(self):
        tmpdir = UnitTestAsTheDefaultExecution.prepare_workdir()
        targetdir = os.path.join(tmpdir.name, "nzb_dir")
        file = find_largest_file_in_glob(targetdir, "**/*.txt")
        self.assertRegex(text=file, expected_regex="real_file/bigger_file.txt")
        tmpdir.cleanup()

    def test_to_process(self):
        tmpdir = UnitTestAsTheDefaultExecution.prepare_workdir()
        to_process = find_targets_for_naming(tmpdir.name)
        print("will process: {} ".format(to_process))

if __name__ == '__main__':
    unittest.main()        