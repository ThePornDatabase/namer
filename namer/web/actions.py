"""
Helper functions to tie in to namer's functionality.
"""
import gzip
import json
import math
import shutil
from enum import Enum
from functools import lru_cache
from pathlib import Path
from queue import Queue
from types import SimpleNamespace
from typing import Dict, List, Optional

import jsonpickle
from werkzeug.routing import Rule

from namer.comparison_results import ComparisonResults, SceneType
from namer.configuration import NamerConfig
from namer.command import gather_target_files_from_dir, is_interesting_movie, is_relative_to, Command
from namer.fileinfo import parse_file_name
from namer.metadataapi import __build_url, __evaluate_match, __request_response_json_object, __metadataapi_response_to_data
from namer.namer import calculate_phash
from namer.videophash import PerceptualHash


class SearchType(str, Enum):
    ANY = 'Any'
    SCENES = 'Scenes'
    MOVIES = 'Movies'
    JAV = 'JAV'


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
    return list(map(lambda o: command_to_file_info(o, config), gather_target_files_from_dir(config.failed_dir, config)))


def get_queued_files(queue: Queue, config: NamerConfig, queue_limit: int = 100) -> List[Dict]:
    """
    Get queued files.
    """
    queue_items = list(queue.queue)[:queue_limit]
    return list(map(lambda x: command_to_file_info(x, config), filter(lambda i: i is not None, queue_items)))


def get_queue_size(queue: Queue) -> int:
    return queue.qsize()


def command_to_file_info(command: Command, config: NamerConfig) -> Dict:
    stat = command.target_movie_file.stat()

    sub_path = str(command.target_movie_file.absolute().relative_to(command.config.failed_dir.absolute())) if is_relative_to(command.target_movie_file, command.config.failed_dir) else None
    res = {
        'file': sub_path,
        'name': command.target_directory.stem if command.parsed_dir_name and command.target_directory else command.target_movie_file.stem,
        'ext': command.target_movie_file.suffix[1:].upper(),
        'update_time': int(stat.st_mtime),
        'size': stat.st_size,
    }

    percentage, phash, oshash = 0.0, '', ''
    if config and config.write_namer_failed_log and config.add_columns_from_log and sub_path:
        log_data = read_failed_log_file(sub_path, config)
        if log_data and log_data.results:
            percentage = max([100 - item.phash_distance * 2.5 if item.phash_distance is not None and item.phash_distance <= 8 else item.name_match for item in log_data.results])
            phash = str(log_data.fileinfo.hashes.phash)
            oshash = log_data.fileinfo.hashes.oshash

    res['percentage'] = percentage
    res['phash'] = phash
    res['oshash'] = oshash

    log_time = 0
    if config and config.add_complete_column and config.write_namer_failed_log and sub_path:
        log_file = command.target_movie_file.parent / (command.target_movie_file.stem + '_namer.json.gz')
        if log_file.is_file():
            log_stat = log_file.stat()
            log_time = int(log_stat.st_ctime)

    res['log_time'] = log_time

    return res


def metadataapi_responses_to_webui_response(responses: Dict, config: NamerConfig, file: str, phash: Optional[PerceptualHash] = None) -> List:
    file = Path(file)
    file_name = file.stem
    if not file.suffix and config.target_extensions:
        file_name += '.' + config.target_extensions[0]

    file_infos = []
    for url, response in responses.items():
        if response and response.strip() != '':
            json_obj = json.loads(response, object_hook=lambda d: SimpleNamespace(**d))
            formatted = json.dumps(json.loads(response), indent=4, sort_keys=True)
            name_parts = parse_file_name(file_name, config)
            file_infos.extend(__metadataapi_response_to_data(json_obj, url, formatted, name_parts, config))

    files = []
    for scene_data in file_infos:
        scene = __evaluate_match(scene_data.original_parsed_filename, scene_data, config, phash).as_dict()
        scene.update(
            {
                'name_parts': scene_data.original_parsed_filename,
                'looked_up': {
                    'uuid': scene_data.uuid,
                    'type': scene_data.type.value,
                    'name': scene_data.name,
                    'date': scene_data.date,
                    'poster_url': scene_data.poster_url,
                    'site': scene_data.site,
                    'network': scene_data.network,
                    'performers': scene_data.performers,
                },
            }
        )
        files.append(scene)

    return files


def get_search_results(query: str, search_type: SearchType, file: str, config: NamerConfig, page: int = 1) -> Dict:
    """
    Search results for user selection.
    """

    responses = {}
    if search_type == SearchType.ANY or search_type == SearchType.SCENES:
        url = __build_url(config, name=query, page=page, scene_type=SceneType.SCENE)
        responses[url] = __request_response_json_object(url, config)

    if search_type == SearchType.ANY or search_type == SearchType.MOVIES:
        url = __build_url(config, name=query, page=page, scene_type=SceneType.MOVIE)
        responses[url] = __request_response_json_object(url, config)

    if search_type == SearchType.ANY or search_type == SearchType.JAV:
        url = __build_url(config, name=query, page=page, scene_type=SceneType.JAV)
        responses[url] = __request_response_json_object(url, config)

    files = metadataapi_responses_to_webui_response(responses, config, query)

    res = {
        'file': file,
        'files': files,
    }

    return res


def get_phash_results(file: str, search_type: SearchType, config: NamerConfig) -> Dict:
    """
    Search results by phash for user selection.
    """

    phash_file = config.failed_dir / file
    if not phash_file.is_file():
        return {}

    phash = calculate_phash(phash_file, config)

    responses = {}
    if search_type == SearchType.ANY or search_type == SearchType.SCENES:
        url = __build_url(config, phash=phash, scene_type=SceneType.SCENE)
        responses[url] = __request_response_json_object(url, config)

    if search_type == SearchType.ANY or search_type == SearchType.MOVIES:
        url = __build_url(config, phash=phash, scene_type=SceneType.MOVIE)
        responses[url] = __request_response_json_object(url, config)

    if search_type == SearchType.ANY or search_type == SearchType.JAV:
        url = __build_url(config, phash=phash, scene_type=SceneType.JAV)
        responses[url] = __request_response_json_object(url, config)

    files = metadataapi_responses_to_webui_response(responses, config, file, phash)

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

    if config.del_other_files and file_name.is_dir():
        target_name = config.failed_dir / Path(file_name_str).parts[0]
        shutil.rmtree(target_name)
    else:
        log_file = config.failed_dir / (file_name.stem + '_namer.json.gz')
        if log_file.is_file():
            log_file.unlink()

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
            for item in decoded.results:
                if not hasattr(item, 'phash_distance'):
                    item.phash_distance = 0 if hasattr(item, 'phash_match') and getattr(item, 'phash_match') else None  # noqa: B009

                if not hasattr(item, 'phash_duration'):
                    item.phash_duration = None

                if not hasattr(item.looked_up, 'hashes'):
                    item.looked_up.hashes = []

            res = decoded

    return res


def is_acceptable_file(file: Path, config: NamerConfig) -> bool:
    """
    Checks if a file belong to namer.
    """
    return str(config.failed_dir) in str(file.resolve()) and file.is_file() and is_interesting_movie(file, config)


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
