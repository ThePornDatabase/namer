import json
from pathlib import Path
from types import SimpleNamespace

from namer.filenameparser import parse_file_name
from namer.metadataapi import __build_url, __get_response_json_object, __jsondata_to_fileinfo, __metadataapi_response_to_data
from namer.namer import move_to_final_location
from namer.types import default_config

config = default_config()


def has_no_empty_params(rule):
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)


def get_files(path: Path) -> list[Path]:
    return [file for file in path.rglob('*.*') if file.is_file() and file.suffix[1:] in config.target_extensions]


def get_search_results(query: str, file: str):
    url = __build_url(query)
    json_response = __get_response_json_object(url, config.porndb_token)
    file_infos = []
    if json_response is not None and json_response.strip() != "":
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


def make_rename(file_name: str, scene_id: str) -> bool:
    file_name = Path(file_name)

    file_name_parts = parse_file_name(file_name.name, config.name_parser)
    url = f'https://api.metadataapi.net/scenes/{scene_id}'

    data = __get_response_json_object(url, config.porndb_token)
    data_res = json.loads(data)
    data_obj = json.loads(data, object_hook=lambda d: SimpleNamespace(**d))
    result = __jsondata_to_fileinfo(data_obj.data, url, data_res, file_name_parts)

    res = move_to_final_location(file_name, config.dest_dir, config.new_relative_path_name, result, config)

    return res.is_file()
