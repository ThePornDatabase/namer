"""
Handle matching data in a FileInfo (likely generated by a namer_file_parser.py) to
look up metadata (actors, studio, creation data, posters, etc) from the porndb.
"""

import argparse
import itertools
import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List, Optional, Tuple
from urllib.parse import quote

import imagehash
import rapidfuzz
from loguru import logger
from PIL import Image
from requests import JSONDecodeError
from unidecode import unidecode

from namer.comparison_results import ComparisonResult, ComparisonResults, HashType, LookedUpFileInfo, Performer, SceneHash, SceneType
from namer.configuration import NamerConfig
from namer.configuration_utils import default_config
from namer.command import make_command, set_permissions, Command
from namer.fileinfo import FileInfo
from namer.http import Http
from namer.videophash import PerceptualHash


def __find_best_match(query: Optional[str], match_terms: List[str], config: NamerConfig) -> Tuple[str, float]:
    powerset_iter = []

    max_size = len(match_terms)
    if config.max_performer_names > 0:
        max_size = min(max_size, config.max_performer_names)

    for length in range(1, max_size + 1):
        data = map(" ".join, itertools.combinations(match_terms, length))
        powerset_iter = itertools.chain(powerset_iter, data)

    ratio = rapidfuzz.process.extractOne(query, choices=powerset_iter)
    return (ratio[0], ratio[1]) if ratio else ratio


def __attempt_better_match(existing: Tuple[str, float], query: Optional[str], match_terms: List[str], namer_config: NamerConfig) -> Tuple[str, float]:
    if existing and existing[1] >= 94.9:  # magic numer
        return existing

    found = __find_best_match(query, match_terms, namer_config)
    if not existing:
        return found

    if not found:
        return "", 0.0

    return existing if existing[1] >= found[1] else found


def __evaluate_match(name_parts: Optional[FileInfo], looked_up: LookedUpFileInfo, namer_config: NamerConfig, phash: Optional[PerceptualHash] = None) -> ComparisonResult:
    site = False
    found_site = None
    release_date = False
    result: Tuple[str, float] = ('', 0.0)

    if name_parts:
        if looked_up.site:
            found_site = re.sub(r"[^a-z0-9]", "", looked_up.site.lower())
            if not name_parts.site:
                site = True
            else:
                site = re.sub(r"[^a-z0-9]", "", name_parts.site.lower()) in found_site or re.sub(r"[^a-z0-9]", "", unidecode(name_parts.site.lower())) in found_site

        if found_site in namer_config.sites_with_no_date_info:
            release_date = True
        else:
            release_date = bool(name_parts.date and (name_parts.date == looked_up.date or unidecode(name_parts.date) == looked_up.date))

        # Full Name
        # Deal with some movies having 50+ performers by throwing performer info away for essamble casts :D
        performers = looked_up.performers
        if len(looked_up.performers) > 6:
            performers = []

        all_performers = list(map(lambda p: p.name, performers))
        if looked_up.name:
            all_performers.insert(0, looked_up.name)

        result = __attempt_better_match(result, name_parts.name, all_performers, namer_config)
        if name_parts.name:
            result = __attempt_better_match(result, unidecode(name_parts.name), all_performers, namer_config)

        # First Name Powerset.
        if result and result[1] < 89.9:
            all_performers = list(map(lambda p: p.name.split(" ")[0], performers))
            if looked_up.name:
                all_performers.insert(0, looked_up.name)

            result = __attempt_better_match(result, name_parts.name, all_performers, namer_config)
            if name_parts.name:
                result = __attempt_better_match(result, unidecode(name_parts.name), all_performers, namer_config)

    phash_distance = None
    if phash:
        hashes_distances = []

        if not looked_up.hashes:
            phash_distance = 8 if looked_up.found_via_phash() else None
        else:
            for item in looked_up.hashes:
                if item.type == HashType.PHASH:
                    try:
                        scene_hash = imagehash.hex_to_hash(item.hash)
                    except ValueError:
                        scene_hash = None

                    if scene_hash:
                        distance = phash.phash - imagehash.hex_to_hash(item.hash)
                        hashes_distances.append(distance)

            phash_distance = min(hashes_distances) if hashes_distances else None

    return ComparisonResult(
        name=result[0],
        name_match=result[1],
        date_match=release_date,
        site_match=site,
        name_parts=name_parts,
        looked_up=looked_up,
        phash_distance=phash_distance
    )


def __update_results(results: List[ComparisonResult], name_parts: Optional[FileInfo], namer_config: NamerConfig, skip_date: bool = False, skip_name: bool = False, scene_type: SceneType = SceneType.SCENE, phash: Optional[PerceptualHash] = None):
    if not results or not results[0].is_match():
        for match_attempt in __get_metadataapi_net_fileinfo(name_parts, namer_config, skip_date, skip_name, scene_type=scene_type, phash=phash):
            if match_attempt.uuid not in [res.looked_up.uuid for res in results]:
                result: ComparisonResult = __evaluate_match(name_parts, match_attempt, namer_config, phash)
                results.append(result)

        for match_attempt in __get_metadataapi_net_fileinfo(name_parts, namer_config, skip_date, skip_name, scene_type=scene_type):
            if match_attempt.uuid not in [res.looked_up.uuid for res in results]:
                result: ComparisonResult = __evaluate_match(name_parts, match_attempt, namer_config, phash)
                results.append(result)

        results = sorted(results, key=__match_weight, reverse=True)

    return results


def __metadata_api_lookup_type(results: List[ComparisonResult], name_parts: Optional[FileInfo], namer_config: NamerConfig, scene_type: SceneType, phash: Optional[PerceptualHash] = None) -> List[ComparisonResult]:
    results = __update_results(results, name_parts, namer_config, scene_type=scene_type, phash=phash)
    results = __update_results(results, name_parts, namer_config, skip_name=True, scene_type=scene_type, phash=phash)

    if name_parts and name_parts.date:
        results = __update_results(results, name_parts, namer_config, skip_date=True, scene_type=scene_type)
        results = __update_results(results, name_parts, namer_config, skip_date=True, skip_name=True, scene_type=scene_type)

    return results


def __metadata_api_lookup(name_parts: FileInfo, namer_config: NamerConfig, phash: Optional[PerceptualHash] = None) -> List[ComparisonResult]:
    scene_type: SceneType = SceneType.SCENE
    if name_parts.site:
        if name_parts.site.strip().lower() in namer_config.movie_data_preferred:
            scene_type = SceneType.MOVIE

    results: List[ComparisonResult] = []
    results: List[ComparisonResult] = __metadata_api_lookup_type(results, name_parts, namer_config, scene_type, phash)
    if not results or not results[0].is_match():
        scene_type = SceneType.MOVIE if scene_type == SceneType.SCENE else SceneType.SCENE
        results: List[ComparisonResult] = __metadata_api_lookup_type(results, name_parts, namer_config, scene_type, phash)

    return results


def __match_weight(result: ComparisonResult) -> float:
    value = 0.00
    if result.phash_distance:
        logger.debug("Phash match with '{} - {} = - {}'", result.looked_up.site, result.looked_up.date, result.looked_up.name)
        value = 1000.00 - result.phash_distance * 100
        if result.site_match:
            value += 100
        if result.date_match:
            value += 100
        if result.name_match:
            value += result.name_match

    if bool(result.site_match and result.date_match and result.name_match and result.name_match >= 94.9):
        logger.debug("Name match of {:.2f} with '{} - {} - {}' for name: {}", value, result.looked_up.site, result.looked_up.date, result.looked_up.name, result.name)
        value += 1000.00
        value = (result.name_match + value) if result.name_match else value

    logger.debug("Match was {:.2f} for {}")
    return value


@logger.catch
def __get_response_json_object(url: str, config: NamerConfig) -> str:
    """
    returns json object with info
    """
    headers = {
        "Authorization": f"Bearer {config.porndb_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "namer-1",
    }
    http = Http.get(url, cache_session=config.cache_session, headers=headers)
    response = ''
    if http.ok:
        response = http.text
    else:
        data = None
        try:
            data = http.json()
        except JSONDecodeError:
            pass

        message = 'Unknown error'
        if data and 'message' in data:
            message = data['message']

        logger.error(f'Server API error: "{message}"')

    return response


@logger.catch
def __post_json_object(url: str, config: NamerConfig, data: Optional[Any] = None) -> str:
    """
    returns json object with info
    """
    headers = {
        "Authorization": f"Bearer {config.porndb_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "namer-1",
    }
    http = Http.post(url, cache_session=config.cache_session, headers=headers, json=data)
    response = ''
    if http.ok:
        response = http.text
    else:
        data = None
        try:
            data = http.json()
        except JSONDecodeError:
            pass

        message = 'Unknown error'
        if data and 'message' in data:
            message = data['message']

        logger.error(f'Server API error: "{message}"')

    return response


@logger.catch
def download_file(url: str, file: Path, config: NamerConfig) -> bool:
    headers = {
        "User-Agent": "namer-1",
    }
    if "metadataapi.net" in url:
        headers["Authorization"] = f"Bearer {config.porndb_token}"

    http_file = Http.download_file(url, headers=headers)
    if http_file:
        file.write_bytes(http_file.getbuffer().tobytes())

    return bool(http_file)


@logger.catch
def get_image(url: str, infix: str, video_file: Optional[Path], config: NamerConfig) -> Optional[Path]:
    if url and video_file:
        file = video_file.parent / (video_file.stem + infix + '.png')
        if url.startswith("http") and not file.exists():
            file.parent.mkdir(parents=True, exist_ok=True)
            if download_file(url, file, config):
                with Image.open(file) as img:
                    img.save(file, 'png')
                set_permissions(file, config)
                return file
            else:
                return

        poster = (video_file.parent / url).resolve()
        return poster if poster.exists() and poster.is_file() else None


@logger.catch
def get_trailer(url: Optional[str], video_file: Optional[Path], namer_config: NamerConfig) -> Optional[Path]:
    """
    returns json object with info
    """
    if namer_config.trailer_location and url and video_file:
        logger.info("Attempting to download trailer")
        location = namer_config.trailer_location[:max([idx for idx, x in enumerate(namer_config.trailer_location) if x == "."])]
        url_parts = url.split("?")[0].split(".")

        ext = "mp4"
        if url_parts and url_parts[-1].lower() in namer_config.target_extensions:
            ext = url_parts[-1]

        trailer_file: Path = video_file.parent / (location + "." + ext)
        trailer_file.parent.mkdir(parents=True, exist_ok=True)
        if not trailer_file.exists() and url.startswith("http"):
            if download_file(url, trailer_file, namer_config):
                set_permissions(trailer_file, namer_config)
                return trailer_file
            else:
                return

        trailer = (video_file.parent / url).resolve()
        return trailer if trailer.exists() and trailer.is_file() else None


def __json_to_fileinfo(data, url: str, json_response: str, name_parts: Optional[FileInfo]) -> LookedUpFileInfo:
    file_info = LookedUpFileInfo()

    data_id = data._id  # pylint: disable=protected-access
    file_info.type = SceneType[data.type.upper()]

    url_part = data.type.lower()
    if file_info.type == SceneType.JAV:
        file_info.uuid = f"{url_part}/{data_id}"
    else:
        file_info.uuid = f"{url_part}s/{data_id}"

    file_info.guid = data.id
    file_info.name = data.title
    file_info.description = data.description
    file_info.date = data.date
    file_info.source_url = data.url

    if hasattr(data, 'external_id'):
        file_info.external_id = data.external_id

    file_info.poster_url = None
    if hasattr(data, 'poster'):
        file_info.poster_url = data.poster

    if hasattr(data, 'background') and data.background:
        file_info.background_url = data.background.large

    if hasattr(data, 'trailer'):
        file_info.trailer_url = data.trailer
    else:
        file_info.trailer_url = None

    file_info.site = data.site.name

    # clean up messy site metadata from adultdvdempire -> tpdb.
    if file_info.type == SceneType.MOVIE:
        file_info.site = re.sub(r'\(.*\)$', '', file_info.site.strip()).strip()

    # This is for backwards compatibility of sha hashes only.
    # remove before updating metadata with phash/oshash, replace with full tpdb url, or fully remove, or get a real uuid.
    # this gets written in to the metadata of a video and effects file hashes.
    file_info.look_up_site_id = data_id

    for json_performer in data.performers:
        if not json_performer.name:
            continue

        performer = Performer(json_performer.name)
        if hasattr(json_performer, "parent") and hasattr(json_performer.parent, "extras"):
            performer.role = json_performer.parent.extras.gender
        elif hasattr(json_performer, "extra"):
            performer.role = json_performer.extra.gender

        if hasattr(json_performer, 'image'):
            performer.image = json_performer.image
        else:
            performer.image = None

        file_info.performers.append(performer)

    file_info.original_query = url
    file_info.original_response = json_response
    file_info.original_parsed_filename = name_parts

    if hasattr(data, 'duration'):
        file_info.duration = data.duration

    tags = []
    if hasattr(data, "tags"):
        for tag in data.tags:
            tags.append(tag.name)

    file_info.tags = tags

    hashes = []
    if hasattr(data, 'hashes'):
        for item in data.hashes:
            data = SceneHash(item.hash, item.type, item.duration)
            hashes.append(data)

    file_info.hashes = hashes

    if hasattr(data, "is_collected"):
        file_info.is_collected = data.is_collected

    return file_info


def __metadataapi_response_to_data(json_object, url: str, json_response: str, name_parts: Optional[FileInfo]) -> List[LookedUpFileInfo]:
    file_infos: List[LookedUpFileInfo] = []
    if hasattr(json_object, "data"):
        if isinstance(json_object.data, list):
            for data in json_object.data:
                found_file_info = __json_to_fileinfo(data, url, json_response, name_parts)
                file_infos.append(found_file_info)
        else:
            found_file_info: LookedUpFileInfo = __json_to_fileinfo(json_object.data, url, json_response, name_parts)
            file_infos.append(found_file_info)

    return file_infos


def __build_url(namer_config: NamerConfig, site: Optional[str] = None, release_date: Optional[str] = None, name: Optional[str] = None, uuid: Optional[str] = None, page: Optional[int] = None, scene_type: Optional[SceneType] = None, phash: Optional[PerceptualHash] = None) -> Optional[str]:
    query = ''
    if uuid:
        query = uuid
    else:
        if scene_type == SceneType.SCENE:
            query = 'scenes'
        elif scene_type == SceneType.MOVIE:
            query = 'movies'
        elif scene_type == SceneType.JAV:
            query = 'jav'

        if phash:
            query += f"?hash={phash.phash}&hashType={HashType.PHASH.value}"
        elif site or release_date or name:
            query += "?parse="

            if site:
                # There is a known issue in tpdb, where site names are not matched due to casing.
                # example Teens3Some fails, but Teens3some succeeds.  Turns out Teens3Some is treated as 'Teens 3 Some'
                # and Teens3some is treated correctly as 'Teens 3some'.  Also, 'brazzersextra' still match 'Brazzers Extra'
                # Hense, the hack of lower casing the site.
                query += quote(re.sub(r"[^a-z0-9]", "", unidecode(site).lower())) + "."

            if release_date:
                query += release_date + "."

            if name:
                query += quote(name)

            if page and page > 1:
                query += f"&page={page}"

            query += "&limit=25"

    return f"{namer_config.override_tpdb_address}/{query}" if query != '' else None


def __get_metadataapi_net_info(url: str, name_parts: Optional[FileInfo], namer_config: NamerConfig):
    json_response = __get_response_json_object(url, namer_config)
    file_infos = []
    if json_response and json_response.strip() != "":
        # logger.debug("json_response: \n{}", json_response)
        json_obj = json.loads(json_response, object_hook=lambda d: SimpleNamespace(**d))
        formatted = json.dumps(json.loads(json_response), indent=4, sort_keys=True)
        file_infos = __metadataapi_response_to_data(json_obj, url, formatted, name_parts)

    return file_infos


def __get_metadataapi_net_fileinfo(name_parts: Optional[FileInfo], namer_config: NamerConfig, skip_date: bool, skip_name: bool, scene_type: SceneType = SceneType.SCENE, phash: Optional[PerceptualHash] = None) -> List[LookedUpFileInfo]:
    if namer_config or phash:
        release_date = name_parts.date if name_parts and not skip_date else None
        name = name_parts.name if name_parts and not skip_name else None
        site = name_parts.site if name_parts else None

        url = __build_url(namer_config, site, release_date, name, scene_type=scene_type, phash=phash)
        if url:
            file_infos = __get_metadataapi_net_info(url, name_parts, namer_config)
            return file_infos

    return []


def get_complete_metadataapi_net_fileinfo(name_parts: Optional[FileInfo], uuid: str, namer_config: NamerConfig) -> Optional[LookedUpFileInfo]:
    url = __build_url(namer_config, uuid=uuid)
    if url:
        file_infos = __get_metadataapi_net_info(url, name_parts, namer_config)
        if file_infos:
            return file_infos[0]


def match(file_name_parts: Optional[FileInfo], namer_config: NamerConfig, phash: Optional[PerceptualHash] = None) -> ComparisonResults:
    """
    Give parsed file name parts, and a porndb token, returns a sorted list of possible matches.
    Matches will appear first.
    """
    results: List[ComparisonResult] = []
    if not file_name_parts:
        results = __metadata_api_lookup_type(results, None, namer_config, SceneType.SCENE, phash)
    else:
        results: List[ComparisonResult] = __metadata_api_lookup(file_name_parts, namer_config, phash)

    comparison_results = sorted(results, key=__match_weight, reverse=True)

    # Works around the porndb not returning all info on search queries by looking up the full data
    # with the uuid of the best match.
    for comparison_result in comparison_results:
        if comparison_result.is_match():
            uuid = comparison_results[0].looked_up.uuid
            if uuid:
                file_infos: Optional[LookedUpFileInfo] = get_complete_metadataapi_net_fileinfo(file_name_parts, uuid, namer_config)
                if file_infos:
                    file_infos.original_query = comparison_results[0].looked_up.original_query
                    comparison_results[0].looked_up = file_infos

    return ComparisonResults(comparison_results)


def toggle_collected(metadata: LookedUpFileInfo, config: NamerConfig):
    if metadata.uuid:
        scene_id = metadata.uuid.rsplit('/', 1)[-1]
        __post_json_object(f"{config.override_tpdb_address}/user/collection?scene_id={scene_id}&type={metadata.type.value}", config=config)


def share_hash(metadata: LookedUpFileInfo, scene_hash: SceneHash, config: NamerConfig):
    data = {
        'type': scene_hash.type.value,
        'hash': scene_hash.hash,
        'duration': scene_hash.duration,
    }

    logger.info(f"Sending {scene_hash.type.value}: {scene_hash.hash} with duration {scene_hash.duration}")
    __post_json_object(f"{config.override_tpdb_address}/{metadata.uuid}/hash", config=config, data=data)


def main(args_list: List[str]):
    """
    Looks up metadata from metadataapi.net base on file name.
    """
    description = """
    Command line interface to look up a suggested name for an adult movie file based on an input string
    that is parsable by namer_file_parser.py
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-c", "--configfile", help="override location for a configuration file.", type=Path)
    parser.add_argument("-f", "--file", help="File we want to provide a match name for.", required=True, type=Path)
    parser.add_argument("-j", "--jsonfile", help="write returned json to this file.", type=Path)
    parser.add_argument("-v", "--verbose", help="verbose, print logs", action="store_true")
    args = parser.parse_args(args=args_list)

    config = default_config(args.configfile.absolute() if args.configfile else None)
    file_name: Optional[Command] = make_command(args.file.absolute(), config, ignore_file_restrictions=True)

    results: Optional[ComparisonResults] = None
    if file_name and file_name.parsed_file:
        results = match(file_name.parsed_file, config)

    if results:
        matched = results.get_match()
        if matched:
            print(matched.looked_up.new_file_name(config.inplace_name, config))
            if args.jsonfile and matched.looked_up and matched.looked_up.original_response:
                Path(args.jsonfile).write_text(matched.looked_up.original_response, encoding="UTF-8")
