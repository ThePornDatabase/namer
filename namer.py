import os
import json
from posixpath import basename
from typing import List, Tuple
import unittest
import tempfile

import rapidfuzz
from namer_types import FileNameParts, LookedUpFileInfo
from namer_dirscanner import find_largest_file_in_glob
from namer_file_parser import parse_file_name
from namer_mutagen import update_mp4_file
from namer_metadataapi import get_response_json_object, metadataapi_response_to_data, getMetadataApiNetFileInfo, get_poster
from distutils.dir_util import copy_tree
from types import SimpleNamespace
from dataclasses import dataclass
import re
import shutil
import rapidfuzz
from pathlib import Path
from datetime import timedelta, date

def_rootdir = './test/'

@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class NamerConfig():
    porndb_token: str
    language: str
    watchdir: str
    workingdir: str
    successfuldir: str
    use_dir_name: bool
    min_file_size: int
    del_other_files: bool
    set_gid: bool
    set_dir_permissions: str
    set_file_permissions: str

    def __str__(self):
        str = "porndb token dir: {}\n".format(self.porndb_token)
        str += "watching dir: {}\n".format(self.watchdir)
        str += "working dir: {}\n".format(self.workingdir)
        str += "destination dir: {}\n".format(self.successfuldir)
        str += "use directory name for matching: {}\n".format(self.use_dir_name)
        str += "prefered language stream to edit mp4 metadata: {}\n".format(self.language)
        str += "minfilesize to modify: {}mb\n".format(self.min_file_size)
        str += "del other files: {}\n".format(self.del_other_files)
        str += "group id to set: {}\n".format(self.set_gid)
        str += "dir permissions to set: {}\n".format(self.set_dir_permissions)
        str += "file permissinos to set: {}\n".format(self.set_file_permissions)
        return str

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


    def test_hard_match(self):
        file_name_parts = parse_file_name('EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.part-1-XXX.mp4')
        with open(os.path.join(self.current,"test","response.json"),'r') as days_file:  
            json_object = json.loads(days_file.read(), object_hook=lambda d: SimpleNamespace(**d))
            looked_up = metadataapi_response_to_data(json_object, "", "", file_name_parts)
            self.assertTrue(evaluateMatch(file_name_parts, looked_up[0]).is_match())


    def test_hard_match_false(self):
        file_name_parts = parse_file_name('DorcelClub-2021-12-23-Aya.Benetti.Megane.Lopez.And.Bella.Tina.json')
        with open(os.path.join(self.current,"test","response.json"),'r') as days_file:  
            json_object = json.loads(days_file.read(), object_hook=lambda d: SimpleNamespace(**d))
            looked_up = metadataapi_response_to_data(json_object, "", "", file_name_parts)
            looked_up[0].original_query = "https://api.metadataapi.net/scenes?parse=DorcelClub%20-%202021-12-23%20-%20Aya.Benetti.Megane.Lopez.And.Bella.Tina.mp4&q=DorcelClub%20-%202021-12-23%20-%20Aya.Benetti.Megane.Lopez.And.Bella.Tina&limit=1"
            match = evaluateMatch(file_name_parts, looked_up[0])
            #with self.assertLogs() as captured:
            #    match.result_str()
            #   self.assertRegex(captured.records[1].getMessage(), "Match               : False")    
            self.assertFalse(match.is_match())


    def ____test_call_metadataapi_net(self):
        tmpdir = UnitTestAsTheDefaultExecution.prepare_workdir()
        url="https://api.metadataapi.net/scenes?parse=EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way&q=Fabulous.Anal.3-Way&limit=5"
        json_object = get_response_json_object(url, def_token)
        self.assertRegex("Carmela Clutch: Fabulous Anal 3-Way!", json_object.data[0].title)
        self.assertRegex("2022-01-03", json_object.data[0].date)
        self.assertRegex("Evil Angel", json_object.data[0].site.name)
        tmpdir.cleanup()        

@dataclass(init=True, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class ComparisonResult:
    name: str
    name_match: float
    sitematch: bool
    datematch: bool
    name_parts: FileNameParts
    looked_up: LookedUpFileInfo


    def is_match(self) -> bool:
        return self.sitematch and self.datematch and self.name_match >= 89.9


def evaluateMatch(name_parts: FileNameParts, looked_up: LookedUpFileInfo) -> ComparisonResult:
    date = name_parts.date == looked_up.date 
    site = re.sub(r' ', '', name_parts.site.capitalize()) == re.sub( r' ', '', looked_up.site.capitalize())
    found_words = looked_up.name
    list_of_options = []
    list_of_options.append(found_words)
    performers = ""
    for lady in list(filter(lambda x: x.role == "Female" ,looked_up.performers)):
        performers += lady.name+" "
        found_words += " "+lady.name
        list_of_options.append(found_words)
        list_of_options.append(performers)
    for dude in list(filter(lambda x: x.role != "Female" ,looked_up.performers)):
        performers += " "+dude.name
        found_words += " "+dude.name
        list_of_options.append(found_words)
        list_of_options.append(performers)
    ratios = rapidfuzz.process.extractOne(name_parts.name,list_of_options)
    return ComparisonResult(ratios[0], ratios[1], date, site, name_parts, looked_up)


def metadata_api_lookup(name_parts: FileNameParts, authtoken) -> List[ComparisonResult]:
    results = []
    for match_attempt in getMetadataApiNetFileInfo(name_parts, authtoken, True, False, False):
        result = evaluateMatch(name_parts, match_attempt)
        results.append(result)
        if result.is_match():
            return results
    for match_attempt in getMetadataApiNetFileInfo(name_parts, authtoken, True, True, False):
        result = evaluateMatch(name_parts, match_attempt)
        results.append(result)
        if result.is_match():
            return results
    for match_attempt in getMetadataApiNetFileInfo(name_parts, authtoken, False, False, False):
        result = evaluateMatch(name_parts, match_attempt)
        results.append(result)
        if result.is_match():
            return results
    for match_attempt in getMetadataApiNetFileInfo(name_parts, authtoken, False, False, True):
        result = evaluateMatch(name_parts, match_attempt)
        results.append(result)
        if result.is_match():
            return results
    
    if len(results) == 0 or not results[-1].is_match():
        name_parts.date =  (date.fromisoformat(name_parts.date)+timedelta(days=-1)).isoformat()
        print("Not found, trying 1 day before: {}".format(name_parts))
        for match_attempt in getMetadataApiNetFileInfo(name_parts, authtoken, False, False, False):
            result = evaluateMatch(name_parts, match_attempt)
            results.append(result)
            if result.is_match():
                return results
        for match_attempt in getMetadataApiNetFileInfo(name_parts, authtoken, False, False, True):
            result = evaluateMatch(name_parts, match_attempt)
            results.append(result)
            if result.is_match():
                return results

    if len(results) == 0 or not results[-1].is_match():
        name_parts.date = (date.fromisoformat(name_parts.date)+timedelta(days=2)).isoformat()
        print("Not found, trying 1 day after: {}".format(name_parts))
        for match_attempt in getMetadataApiNetFileInfo(name_parts, authtoken, False, False, False):
            result = evaluateMatch(name_parts, match_attempt)
            results.append(result)
            if result.is_match():
                return results
        for match_attempt in getMetadataApiNetFileInfo(name_parts, authtoken, False, False, True):
            result = evaluateMatch(name_parts, match_attempt)
            results.append(result)
            if result.is_match():
                return results
    return results


def match_percent(result: ComparisonResult) -> float:
    addvalue=0.00
    if result.is_match() == True:
        addvalue=1000.00
    value = result.name_match + addvalue
    print("Name match was {0:.2f} for {1}".format(value, result.name))
    return value


def write_log_file(dir: str, match_attempts: List[ComparisonResult]) -> str:
    logname = os.path.join(dir, "namer.log")
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
        os.chmod(file, int(config.set_dir_permissions, 8))           
    elif not config.set_file_permissions is None:
        os.chmod(file, int(config.set_file_permissions, 8))
    if not config.set_gid is None: 
        os.chown(file, uid=os.getuid(), gid=config.set_gid)

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

def process(file_to_process: str, config: NamerConfig):
    found = determineFile(file_to_process, config)
    parts = moveFiles(found[0], found[1], config)
    dir = parts[0]
    file = parts[1]
    if config.use_dir_name:
        name = os.path.basename(dir)+".mp4"
    else:
        name = os.path.splitext(os.path.basename(file))[0]+".mp4"

    if dir != None and file != None:
        #remove sample files
        print("Processing: {}".format(name))
        file_name_parts = parse_file_name(name)
        comparison_results = metadata_api_lookup(file_name_parts, config.porndb_token)
        comparison_results = sorted(comparison_results, key=match_percent, reverse=True)
        logfile = write_log_file(dir, comparison_results)
        setPermissions(logfile, config)
        result = comparison_results[0]
        if result.is_match() == True:
            print("Downloading poster: {}".format(result.looked_up.poster_url))
            poster = get_poster(result.looked_up.poster_url, config.porndb_token, dir)
            setPermissions(poster, config)
            print("Updating file metadata (atoms): {}".format(file))
            update_mp4_file(result.looked_up, file, dir, poster, config.language)
            finalfile = os.path.join(config.successfuldir, os.path.splitext(result.looked_up.new_file_name())[0])
            print("Moving: {} to {}".format(dir, finalfile))
            os.rename(dir, finalfile)
            setPermissions(finalfile, config)
            print("Done processing {}".format(file_to_process))


if __name__ == '__main__':
    unittest.main()

