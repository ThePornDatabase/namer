import os
import json
from random import choices
import string
from datetime import timedelta, date
import pathlib
import re
from typing import List
import sys
import getopt
import logging
from types import SimpleNamespace
import urllib
import urllib.request
import rapidfuzz
from namer_types import LookedUpFileInfo, Performer, FileNameParts, ComparisonResult, defaultConfig
from namer_file_parser import parse_file_name

logger = logging.getLogger('metadata')


def __evaluate_match(name_parts: FileNameParts, looked_up: LookedUpFileInfo) -> ComparisonResult:
    release_date = name_parts.date == looked_up.date
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
    return ComparisonResult(ratios[0], ratios[1], release_date, site, name_parts, looked_up)


def __metadata_api_lookup(name_parts: FileNameParts, authtoken: str) -> List[ComparisonResult]:
    results = []
    for match_attempt in __get_metadataapi_net_fileinfo(name_parts, authtoken, True, False, False):
        result = __evaluate_match(name_parts, match_attempt)
        results.append(result)
        if result.is_match():
            return results
    for match_attempt in __get_metadataapi_net_fileinfo(name_parts, authtoken, True, True, False):
        result = __evaluate_match(name_parts, match_attempt)
        results.append(result)
        if result.is_match():
            return results
    for match_attempt in __get_metadataapi_net_fileinfo(name_parts, authtoken, False, False, False):
        result = __evaluate_match(name_parts, match_attempt)
        results.append(result)
        if result.is_match():
            return results
    for match_attempt in __get_metadataapi_net_fileinfo(name_parts, authtoken, False, False, True):
        result = __evaluate_match(name_parts, match_attempt)
        results.append(result)
        if result.is_match():
            return results

    if len(results) == 0 or not results[-1].is_match():
        name_parts.date =  (date.fromisoformat(name_parts.date)+timedelta(days=-1)).isoformat()
        logger.info("Not found, trying 1 day before: %s",name_parts)
        for match_attempt in __get_metadataapi_net_fileinfo(name_parts, authtoken, False, False, False):
            result = __evaluate_match(name_parts, match_attempt)
            results.append(result)
            if result.is_match():
                return results
        for match_attempt in __get_metadataapi_net_fileinfo(name_parts, authtoken, False, False, True):
            result = __evaluate_match(name_parts, match_attempt)
            results.append(result)
            if result.is_match():
                return results

    if len(results) == 0 or not results[-1].is_match():
        name_parts.date = (date.fromisoformat(name_parts.date)+timedelta(days=2)).isoformat()
        logger.info("Not found, trying 1 day after: %s",name_parts)
        for match_attempt in __get_metadataapi_net_fileinfo(name_parts, authtoken, False, False, False):
            result = __evaluate_match(name_parts, match_attempt)
            results.append(result)
            if result.is_match():
                return results
        for match_attempt in __get_metadataapi_net_fileinfo(name_parts, authtoken, False, False, True):
            result = __evaluate_match(name_parts, match_attempt)
            results.append(result)
            if result.is_match():
                return results
    return results


def __match_percent(result: ComparisonResult) -> float:
    addvalue=0.00
    if result.is_match() is True:
        addvalue=1000.00
    value = result.name_match + addvalue
    logger.info("Name match was %.2f for %s", value, result.name)
    return value


def __get_response_json_object(url: str, authtoken: str) -> str:
    """
    returns json object with info
    """
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {authtoken}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header('User-Agent', 'namer-1')

    try:
        with urllib.request.urlopen(req) as response:
            html = response.read()
            return html
    except urllib.error.HTTPError as ex:
        logger.warning(ex)
        return None


def get_poster(url: str, authtoken: str, video_file: str) -> str:
    """
    returns json object with info
    """
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {authtoken}")
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)')
    random = ''.join(choices(population=string.ascii_uppercase + string.digits, k=10))
    file = os.path.splitext(video_file)[0]+"_"+random+"_poster"+pathlib.Path(url).suffix
    with urllib.request.urlopen(req) as response:
        content = response.read()
        with open(file, "wb") as binary_file:
            # Write bytes to file
            binary_file.write(content)
    return file

def __jsondata_to_fileinfo(data, url, json_response, name_parts) -> LookedUpFileInfo:
    file_info = LookedUpFileInfo()
    file_info.uuid = data._id # pylint: disable=protected-access
    file_info.name = data.title
    file_info.description = data.description
    file_info.date = data.date
    file_info.source_url = data.url
    file_info.poster_url = data.poster
    file_info.site = data.site.name
    file_info.look_up_site_id = data._id # pylint: disable=protected-access
    for json_performer in data.performers:
        performer = Performer()
        if hasattr(json_performer, "parent") and hasattr(json_performer.parent, "extras"):
            performer.role = json_performer.parent.extras.gender
        performer.name = json_performer.name
        file_info.performers.append(performer)
    file_info.original_query=url
    file_info.original_response=json_response
    file_info.original_parsed_filename=name_parts
    tags = []
    if hasattr(data, "tags"):
        for tag in data.tags:
            tags.append(tag.name)
        file_info.tags = tags
    return file_info


def __metadataapi_response_to_data(json_object, url, json_response, name_parts) -> List[LookedUpFileInfo]:
    file_infos = []
    if hasattr(json_object, "data"):
        if isinstance(json_object.data, list):
            for data in json_object.data:
                found_file_info = __jsondata_to_fileinfo(data, url, json_response, name_parts)
                file_infos.append(found_file_info)
        else:
            file_infos.append(__jsondata_to_fileinfo(json_object.data, url, json_response, name_parts))
    return file_infos


def __build_url(site:str=None, release_date:str=None, name:str=None, uuid:str=None) -> str:
    query = ""
    if uuid is not None:
        query = "/"+uuid
    else:
        query="?q="
        if site is not None:
            query += urllib.parse.quote(re.sub(r' ', '.', site))+"."
        if release_date is not None:
            query += release_date+"."
        if name is not None:
            query += urllib.parse.quote(re.sub(r' ', '.', name))
        query+="&limit=1"
    return f"https://api.metadataapi.net/scenes{query}"


def __get_metadataapi_net_fileinfo(name_parts: FileNameParts, authtoken: str, skipdate: bool, skipsite: bool, skipname: bool) -> List[LookedUpFileInfo]:
    release_date = name_parts.date if not skipdate else None
    site = name_parts.site if not skipsite else None
    name = name_parts.name if not skipname else None
    url = __build_url(site, release_date, name)
    logger.info("Querying: %s",url)
    json_response = __get_response_json_object(url, authtoken)
    file_infos = []
    if json_response is not None and json_response.strip() != '':
        logger.debug("json_repsonse: \n%s", json_response)
        json_obj = json.loads(json_response, object_hook=lambda d: SimpleNamespace(**d))
        formatted = json.dumps(json.loads(json_response), indent=4, sort_keys=True)
        file_infos = __metadataapi_response_to_data(json_obj, url, formatted, name_parts)
    return file_infos


def __get_complete_metadatapi_net_fileinfo(name_parts: FileNameParts, uuid: str, authtoken: str) -> LookedUpFileInfo:
    url = __build_url(uuid=uuid)
    logger.info("Querying: %s",url)
    json_response = __get_response_json_object(url, authtoken)
    file_infos = []
    if json_response is not None and json_response.strip() != '':
        logger.debug("json_repsonse: \n%s",json_response)
        json_obj = json.loads(json_response, object_hook=lambda d: SimpleNamespace(**d))
        formatted = json.dumps(json.loads(json_response), indent=4, sort_keys=True)
        file_infos = __metadataapi_response_to_data(json_obj, url, formatted, name_parts)
    if len(file_infos) > 0:
        return file_infos[0]
    return None

def match(file_name_parts: FileNameParts, porndb_token: str) -> List[ComparisonResult]:
    """
    Give parsed file name parts, and a porndb token, returns a sorted list of possible matches.
    Matches will appear first.
    """
    comparison_results = __metadata_api_lookup(file_name_parts, porndb_token)
    comparison_results = sorted(comparison_results, key=__match_percent, reverse=True)
    # Works around the porndb not returning all info on search queries by looking up the full data
    # with the uuid of the best match.
    if len(comparison_results) > 0 and comparison_results[0].is_match is True:
        file_infos =  __get_complete_metadatapi_net_fileinfo(file_name_parts, comparison_results[0].looked_up.uuid ,porndb_token)
        if file_infos is not None:
            comparison_results[0].looked_up = file_infos
    return comparison_results


def usage():
    print("-h: this message")
    print("-q: hide all messages")
    print("-f: file (or name) to use for lookup from the porndb")
    print("-t: bearer token to use for the porndb")


def main(argv):
    porndb_token = None
    filetoprocess = None
    logger_level = logging.DEBUG
    try:
        opts, __args = getopt.getopt(argv,"hqf:t:",["configfile=","file=","porndb_token="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            usage()
            sys.exit()
        if opt == '-q':
            logger_level=logging.ERROR
        elif opt in ("-f", "--file"):
            filetoprocess = arg
        elif opt in ("-t", "--token"):
            porndb_token = arg
    if filetoprocess is None or porndb_token is None:
        usage()
        sys.exit(2)
    else:
        logging.basicConfig(level=logger_level)
        name = parse_file_name(os.path.basename(filetoprocess))
        results = match(name, porndb_token)
        if len(results) > 0 and results[0].is_match() is True:
            print(results[0].looked_up.new_file_name(defaultConfig().inplace_name))


if __name__ == "__main__":
    main(sys.argv[1:])
    sys.exit(0)
