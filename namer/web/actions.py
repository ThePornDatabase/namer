"""
Helper functions to tie in to namer's functionality.
"""
import gzip
import json
import math
import shutil
from functools import lru_cache
from pathlib import Path
from queue import Queue
from types import SimpleNamespace
from typing import Dict, List, Optional

import jsonpickle
from werkzeug.routing import Rule

from namer.comparison_results import ComparisonResults
from namer.configuration import NamerConfig
from namer.command import gather_target_files_from_dir, is_interesting_movie, subpath_or_equal, Command
from namer.metadataapi import __build_url, __get_response_json_object, __metadataapi_response_to_data  # type: ignore


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


def get_queued_files(queue: Queue, queue_limit: int = 100) -> List[Dict]:
    """
    Get queued files.
    """
    queue_items = list(queue.queue)[:queue_limit]
    return list(map(command_to_file_info, filter(lambda i: i is not None, queue_items)))


def get_queue_size(queue: Queue) -> int:
    return queue.qsize()


def command_to_file_info(command: Command) -> Dict:
    stat = command.target_movie_file.stat()
    return {
        'file': str(command.target_movie_file.relative_to(command.config.failed_dir)) if subpath_or_equal(command.target_movie_file, command.config.failed_dir) else None,
        'name': command.target_directory.stem if command.parsed_dir_name and command.target_directory else command.target_movie_file.stem,
        'ext': command.target_movie_file.suffix[1:].upper(),
        'size_byte': stat.st_size,
        'size': convert_size(stat.st_size),
    }


def get_search_results(query: str, search_type: str, file: str, config: NamerConfig, page: int = 1) -> Dict:
    """
    Search results for user selection.
    """

    responses = {}
    if search_type == 'Any' or search_type == 'Scenes':
        # scenes
        url = __build_url(config, name=query, page=page, movie=False)
        responses[url] = __get_response_json_object(url, config)

    if search_type == 'Any' or search_type == 'Movies':
        # movies
        url = __build_url(config, name=query, page=page, movie=True)
        responses[url] = __get_response_json_object(url, config)

    file_infos = []
    for url, response in responses.items():
        if response and response.strip() != '':
            json_obj = json.loads(response, object_hook=lambda d: SimpleNamespace(**d))
            formatted = json.dumps(json.loads(response), indent=4, sort_keys=True)
            file_infos.extend(__metadataapi_response_to_data(json_obj, url, formatted, None))

    files = []
    for scene_data in file_infos:
        scene = {
            'id': scene_data.uuid,
            'type': scene_data.type,
            'title': scene_data.name,
            'date': scene_data.date,
            'poster': scene_data.poster_url,
            'site': scene_data.site,
            'tags_count': len(scene_data.tags),
            'performers': scene_data.performers,
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


def read_failed_log_file(name: str, config: NamerConfig) -> Optional[ComparisonResults]:
    file = config.failed_dir / name
    file = file.parent / (file.stem + '_namer.json.gz')

    res: Optional[ComparisonResults] = None
    if file.is_file():
        res = _read_failed_log_file(file, file.stat().st_size, file.stat().st_mtime)

    return res


@lru_cache(maxsize=1024)
def _read_failed_log_file(file: Path, file_size: int, file_update: float) -> Optional[ComparisonResults]:
    res: Optional[ComparisonResults] = None
    if file.is_file():
        data = gzip.decompress(file.read_bytes())
        decoded = jsonpickle.decode(data)
        if decoded and isinstance(decoded, ComparisonResults):
            res = decoded

    return res


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
        return '0 B'

    size = 1024
    size_name = ('B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB')
    i = int(math.floor(math.log(size_bytes, size)))
    p = math.pow(size, i)
    s = round(size_bytes / p, 2)

    return f'{s:.2f} {size_name[i]}'


def human_format(num):
    if num == 0:
        return '0'

    size = 1000
    size_name = ('', 'K', 'M', 'B', 'T')
    i = int(math.floor(math.log(num, size)))
    p = math.pow(size, i)
    s = str(round(num / p, 2))
    s = s.rstrip('0').rstrip('.')

    return f'{s}{size_name[i]}'
