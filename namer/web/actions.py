"""
Helper functions to tie in to namer's functionality.
"""

import json
import math
import shutil
from pathlib import Path
from queue import Queue
from types import SimpleNamespace
from typing import Dict, List

from werkzeug.routing import Rule

from namer.fileutils import gather_target_files_from_dir, is_interesting_movie, subpath_or_equal
from namer.metadataapi import __build_url, __get_response_json_object, __metadataapi_response_to_data  # type: ignore
from namer.types import Command, NamerConfig


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
    return list(map(command_to_file_info, gather_target_files_from_dir(config.failed_dir, config)))


def get_queued_files(queue: Queue) -> List[Dict]:
    """
    Get queued files.
    """
    return list(map(command_to_file_info, filter(lambda i: i is not None, queue.queue)))


def get_queue_size(queue: Queue) -> int:
    return queue.qsize()


def command_to_file_info(command: Command) -> Dict:
    return {
        'file': str(command.target_movie_file.relative_to(command.config.failed_dir)) if subpath_or_equal(command.target_movie_file, command.config.failed_dir) else None,
        'name': command.target_directory.stem if command.parsed_dir_name and command.target_directory is not None else command.target_movie_file.stem,
        'ext': command.target_movie_file.suffix[1:].upper(),
        'size': convert_size(command.target_movie_file.stat().st_size),
    }


def get_search_results(query: str, file: str, config: NamerConfig) -> Dict:
    """
    Search results for user selection.
    """
    url = __build_url(name=query)
    json_response = __get_response_json_object(url, config)
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


def delete_file(file_name_str: str, config: NamerConfig) -> bool:
    """
    Delete selected file.
    """
    file_name = config.failed_dir / file_name_str
    if not is_acceptable_file(file_name, config) or not config.allow_delete_files:
        return False

    if config.del_other_files:
        target_name = config.failed_dir / Path(file_name_str).parts[0]
        shutil.rmtree(target_name)
    else:
        file_name.unlink()

    return not file_name.is_file()


def is_acceptable_file(file: Path, config: NamerConfig) -> bool:
    """
    Checks if a file belong to namer.
    """
    return str(config.failed_dir) in str(file.resolve()) and file.is_file() and is_interesting_movie(file, config)


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
