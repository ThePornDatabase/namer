"""
Helper functions to tie in to namer's functionality.
"""

import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List

from werkzeug.routing import Rule

from namer.filenameparser import parse_file_name
from namer.metadataapi import __build_url, __get_response_json_object, __jsondata_to_fileinfo, __metadataapi_response_to_data  # type: ignore
from namer.namer import add_extra_artifacts, move_to_final_location
from namer.types import FileNameParts, LookedUpFileInfo, NamerConfig, ProcessingResults


def has_no_empty_params(rule: Rule) -> bool:
    """
    Currently unused, useful to inspect Flask rules.
    """
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)


def get_failed_files(config: NamerConfig) -> List[Dict]:
    """
    Get failed files to rename.
    """
    files = [file for file in config.failed_dir.rglob('*.*') if is_acceptable_file(file, config)]
    res = []
    for file in files:
        file_rel = file.relative_to(config.failed_dir)
        res.append({
            'file': str(file_rel),
            'name': file.stem,
            'ext': file.suffix[1:].upper(),
            'size': convert_size(file.stat().st_size),
        })

    return res


def get_search_results(query: str, file: str, config: NamerConfig) -> Dict:
    """
    Search results for user selection.
    """
    url = __build_url(query)
    json_response = __get_response_json_object(url, config.porndb_token)
    file_infos = []
    if json_response is not None and json_response.strip() != '':
        json_obj = json.loads(json_response, object_hook=lambda d: SimpleNamespace(**d))
        formatted = json.dumps(json.loads(json_response), indent=4, sort_keys=True)
        file_infos = __metadataapi_response_to_data(json_obj, url, formatted, None)

    files = []
    for scene_data in file_infos:
        scene = {
            'id': scene_data.uuid,
            'title': scene_data.name,
            'date': scene_data.date,
            'poster': scene_data.poster_url,
        }
        files.append(scene)

    res = {
        'file': file,
        'files': files,
    }

    return res


def make_rename(file_name_str: str, scene_id: str, config: NamerConfig) -> bool:
    """
    Rename selected file.
    """
    file_name = config.failed_dir / file_name_str
    if not is_acceptable_file(file_name, config):
        return False

    file_name_parts: FileNameParts = parse_file_name(file_name.name, config.name_parser)
    url = f'https://api.metadataapi.net/scenes/{scene_id}'

    data: str = __get_response_json_object(url, config.porndb_token)
    data_res = json.loads(data)
    data_obj = json.loads(data, object_hook=lambda d: SimpleNamespace(**d))
    result: LookedUpFileInfo = __jsondata_to_fileinfo(data_obj.data, url, data_res, file_name_parts)

    res = move_to_final_location(file_name, config.dest_dir, config.new_relative_path_name, result, config)

    processing: ProcessingResults = ProcessingResults()
    processing.new_metadata = result
    processing.parsed_file = file_name_parts
    processing.video_file = res

    add_extra_artifacts(processing, config)

    return res is not None and res.is_file()


def delete_file(file_name_str: str, config: NamerConfig) -> bool:
    """
    Delete selected file.
    """
    file_name = config.failed_dir / file_name_str
    if not is_acceptable_file(file_name, config) or not config.allow_delete_files:
        return False

    file_name.unlink(True)

    return not file_name.is_file()


def is_acceptable_file(file: Path, config: NamerConfig) -> bool:
    """
    Checks if a file belong to namer.
    """
    return str(config.failed_dir) in str(file.resolve()) and file.is_file() and file.suffix[1:] in config.target_extensions


def convert_size(size_bytes: int) -> str:
    """
    Convert int to size string.
    """
    if size_bytes == 0:
        return '0B'

    size = 1024
    size_name = ('B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB')
    i = int(math.floor(math.log(size_bytes, size)))
    p = math.pow(size, i)
    s = round(size_bytes / p, 2)

    return f'{s} {size_name[i]}'
