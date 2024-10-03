"""
Namer Configuration readers/verifier
"""

import json
import os
import random
import re
import shutil
from importlib import resources
from typing import Dict, List, Optional, Callable, Pattern, Any, Tuple
from configupdater import ConfigUpdater
from pathlib import Path

from loguru import logger

from namer import database
from namer.configuration import NamerConfig
from namer.ffmpeg import FFMpeg
from namer.name_formatter import PartialFormatter


def __verify_naming_config(config: NamerConfig, formatter: PartialFormatter) -> bool:
    """
    Verifies the contents of your config file. Returns False if configuration failed.
    """
    success = True
    if not config.enable_metadataapi_genres and not config.default_genre:
        logger.error('Since enable_metadataapi_genres is not True, you must specify a default_genre')
        success = False

    success = __verify_name_string(formatter, 'inplace_name', config.inplace_name) and success

    return success


def __verify_watchdog_config(config: NamerConfig, formatter: PartialFormatter) -> bool:
    """
    Verifies the contents of your config file. Returns False if configuration failed.
    """
    success = True
    if not config.enable_metadataapi_genres and not config.default_genre:
        logger.error('Since enable_metadataapi_genres is not True, you must specify a default_genre')
        success = False

    watchdog_dirs = ['watch_dir', 'work_dir', 'failed_dir', 'dest_dir']
    for dir_name in watchdog_dirs:
        success = __verify_dir(config, dir_name, [name for name in watchdog_dirs if dir_name != name]) and success

    success = __verify_name_string(formatter, 'new_relative_path_name', config.new_relative_path_name) and success

    return success


def __verify_dir(config: NamerConfig, name: str, other_dirs: List[str]) -> bool:
    """
    verify a config directory exist. return false if verification fails
    """
    path_list = tuple(str(getattr(config, name)) for name in other_dirs if hasattr(config, name))
    dir_name: Optional[Path] = getattr(config, name) if hasattr(config, name) else None
    if dir_name and (not dir_name.is_dir() or str(dir_name).startswith(path_list)):
        logger.error(f'Configured directory {name}: "{dir_name}" is not a directory or not exist or in other watchdog directory')

        return False

    min_size = config.min_file_size if config.min_file_size else 1
    if dir_name and name == 'work_dir' and sum(file.stat().st_size for file in config.work_dir.rglob('*')) / 1024 / 1024 > min_size:
        logger.error(f'Configured directory {name}: "{dir_name}" should be empty')

        return False

    if dir_name and not os.access(dir_name, os.W_OK):
        logger.warning(f'Configured directory {name}: "{dir_name}" might have write permission problem')

    return True


def __verify_name_string(formatter: PartialFormatter, name: str, name_string: str) -> bool:
    """
    Verify the name format string.
    """
    values = dict(zip(formatter.supported_keys, formatter.supported_keys))
    try:
        formatter.format(name_string, values)
        return True
    except KeyError as key_error:
        logger.error('Configuration {} is not a valid file name format, please check {}', name, name_string)
        logger.error('Error message: {}', key_error)
        return False


def __verify_ffmpeg(ffmpeg: FFMpeg) -> bool:
    versions = ffmpeg.ffmpeg_version()
    for tool, version in versions.items():
        if not version:
            logger.error(f'No {tool} found, please install {tool}')
        else:
            logger.info(f'{tool} version "{version}" found')

    return None not in versions.values()


def verify_configuration(config: NamerConfig, formatter: PartialFormatter) -> bool:
    """
    Can verify a NamerConfig with a formatter
    """
    success = __verify_naming_config(config, formatter)
    success = __verify_watchdog_config(config, formatter) and success
    success: bool = __verify_ffmpeg(config.ffmpeg) and success

    return success


# Read and write .ini files utils below


def get_str(updater: ConfigUpdater, section: str, key: str) -> Optional[str]:
    """
    Read a string from an ini file if the config exists, else return None if the config does not
    exist in file.
    """
    if updater.has_option(section, key):
        output = updater.get(section, key)
        return str(output.value) if output.value else output.value


# Ini file string converters, to and from NamerConfig type


def to_bool(value: Optional[str]) -> Optional[bool]:
    return value.lower() == 'true' if value else None


def from_bool(value: Optional[bool]) -> str:
    return str(value) if value is not None else ''


def to_str_list_lower(value: Optional[str]) -> List[str]:
    return [x.strip().lower() for x in value.lower().split(',')] if value else []


def from_str_list_lower(value: Optional[List[str]]) -> str:
    return ', '.join(value) if value else ''


def to_int(value: Optional[str]) -> Optional[int]:
    return int(value) if value is not None else None


def from_int(value: Optional[int]) -> str:
    return str(value) if value is not None else ''


def to_path(value: Optional[str]) -> Optional[Path]:
    return Path(value).resolve() if value else None


def from_path(value: Optional[Path]) -> str:
    return str(value) if value else ''


def to_regex_list(value: Optional[str]) -> List[Pattern]:
    return [re.compile(x.strip()) for x in value.split(',')] if value else []


def from_regex_list(value: Optional[List[Pattern]]) -> str:
    return ', '.join([x.pattern for x in value]) if value else ''


def to_site_abbreviation(site_abbreviations: Optional[str]) -> Dict[Pattern, str]:
    abbreviations_db = database.abbreviations.copy()
    if site_abbreviations:
        data = json.loads(site_abbreviations)
        abbreviations_db.update(data)

    new_abbreviation: Dict[Pattern, str] = {}
    for abbreviation, full in abbreviations_db.items():
        key = re.compile(rf'^{abbreviation}[ .-]+', re.IGNORECASE)
        new_abbreviation[key] = f'{full} '

    return new_abbreviation


def from_site_abbreviation(site_abbreviations: Optional[Dict[Pattern, str]]) -> str:
    out: Dict[str, str] = {x.pattern[1:-6]: y[0:-1] for (x, y) in site_abbreviations.items()} if site_abbreviations else {}
    res = json.dumps(out)

    return res


def to_pattern(value: Optional[str]) -> Optional[Pattern]:
    return re.compile(value, re.IGNORECASE) if value else None


def from_pattern(value: Optional[Pattern]) -> str:
    return value.pattern if value else ''


def to_site_list(value: Optional[str]) -> List[str]:
    return [re.sub(r'[^a-z0-9]', '', x.strip().lower()) for x in value.split(',')] if value else []


def set_str(updater: ConfigUpdater, section: str, key: str, value: str) -> None:
    updater[section][key].value = value


def set_comma_list(updater: ConfigUpdater, section: str, key: str, value: List[str]) -> None:
    updater[section][key].value = ', '.join(value)


def set_int(updater: ConfigUpdater, section: str, key: str, value: int) -> None:
    updater[section][key].value = str(value)


def set_boolean(updater: ConfigUpdater, section: str, key: str, value: bool) -> None:
    updater[section][key] = str(value)


field_info: Dict[str, Tuple[str, Optional[Callable[[Optional[str]], Any]], Optional[Callable[[Any], str]]]] = {
    'porndb_token': ('namer', None, None),
    'name_parser': ('namer', None, None),
    'inplace_name': ('namer', None, None),
    'prefer_dir_name_if_available': ('namer', to_bool, from_bool),
    'min_file_size': ('namer', to_int, from_int),
    'write_namer_log': ('namer', to_bool, from_bool),
    'write_namer_failed_log': ('namer', to_bool, from_bool),
    'target_extensions': ('namer', to_str_list_lower, from_str_list_lower),
    'update_permissions_ownership': ('namer', to_bool, from_bool),
    'set_dir_permissions': ('namer', to_int, from_int),
    'set_file_permissions': ('namer', to_int, from_int),
    'set_uid': ('namer', to_int, from_int),
    'set_gid': ('namer', to_int, from_int),
    'trailer_location': ('namer', None, None),
    'convert_container_to': ('namer', None, None),
    'sites_with_no_date_info': ('namer', to_str_list_lower, from_str_list_lower),
    'movie_data_preferred': ('namer', to_str_list_lower, from_str_list_lower),
    'vr_studios': ('namer', to_str_list_lower, from_str_list_lower),
    'vr_tags': ('namer', to_str_list_lower, from_str_list_lower),
    'site_abbreviations': ('namer', to_site_abbreviation, from_site_abbreviation),
    'max_performer_names': ('namer', to_int, from_int),
    'use_database': ('namer', to_bool, from_bool),
    'database_path': ('namer', to_path, from_path),
    'use_requests_cache': ('namer', to_bool, from_bool),
    'requests_cache_expire_minutes': ('namer', to_int, from_int),
    'override_tpdb_address': ('namer', None, None),
    'plex_hack': ('namer', to_bool, from_bool),
    'path_cleanup': ('namer', to_bool, from_bool),
    'search_phash': ('Phash', to_bool, from_bool),
    'send_phash': ('Phash', to_bool, from_bool),
    'use_alt_phash_tool': ('Phash', to_bool, from_bool),
    'max_ffmpeg_workers': ('Phash', to_int, from_int),
    'use_gpu': ('Phash', to_bool, from_bool),
    'mark_collected': ('metadata', to_bool, from_bool),
    'write_nfo': ('metadata', to_bool, from_bool),
    'enabled_tagging': ('metadata', to_bool, from_bool),
    'enabled_poster': ('metadata', to_bool, from_bool),
    'download_type': ('metadata', to_str_list_lower, from_str_list_lower),
    'enable_metadataapi_genres': ('metadata', to_bool, from_bool),
    'default_genre': ('metadata', None, None),
    'language': ('metadata', None, None),
    'preserve_duplicates': ('duplicates', to_bool, from_bool),
    'max_desired_resolutions': ('duplicates', to_int, from_int),
    'desired_codec': ('duplicates', to_str_list_lower, from_str_list_lower),
    'ignored_dir_regex': ('watchdog', to_pattern, from_pattern),
    'del_other_files': ('watchdog', to_bool, from_bool),
    'extra_sleep_time': ('watchdog', to_int, from_int),
    'queue_limit': ('watchdog', to_int, from_int),
    'queue_sleep_time': ('watchdog', to_int, from_int),
    'new_relative_path_name': ('watchdog', None, None),
    'watch_dir': ('watchdog', to_path, from_path),
    'work_dir': ('watchdog', to_path, from_path),
    'failed_dir': ('watchdog', to_path, from_path),
    'dest_dir': ('watchdog', to_path, from_path),
    'retry_time': ('watchdog', None, None),
    'web': ('watchdog', to_bool, from_bool),
    'port': ('watchdog', to_int, from_int),
    'host': ('watchdog', None, None),
    'web_root': ('watchdog', None, None),
    'allow_delete_files': ('watchdog', to_bool, from_bool),
    'add_columns_from_log': ('watchdog', to_bool, from_bool),
    'add_complete_column': ('watchdog', to_bool, from_bool),
    'debug': ('watchdog', to_bool, from_bool),
    'console_format': ('watchdog', None, None),
    'manual_mode': ('watchdog', to_bool, from_bool),
    'diagnose_errors': ('watchdog', to_bool, from_bool),
}
"""
A mapping from NamerConfig field to ini file section - the ini property name and the field name
must be identical.   The conversion of string too and from functions are also provided here allowing
the conversion of types from NamerConfig to and from strings.   If the converters are not set then the
the string is unaltered.
"""


def to_ini(config: NamerConfig) -> str:
    updater = config.config_updater
    for name in field_info.keys():
        info = field_info.get(name)
        if info:
            section = info[0]
            if section:
                value = getattr(config, name)
                convert: Optional[Callable[[Any], str]] = info[2]
                if convert:
                    updater.get(section, name).value = convert(value)
                else:
                    updater.get(section, name).value = value

    return str(updater)


def from_config(config: ConfigUpdater, namer_config: NamerConfig) -> NamerConfig:
    """
    Given a config parser pointed at a namer.cfg file, return a NamerConfig with the file's parameters.
    """
    keys = field_info.keys()
    for name in keys:
        info = field_info.get(name)
        if info and info[0]:
            new_value = get_str(config, info[0], name)
            if new_value or not hasattr(namer_config, name):
                type_converter_lambda: Optional[Callable[[Optional[str]], Any]] = info[1]
                if type_converter_lambda:
                    setattr(namer_config, name, type_converter_lambda(new_value))
                else:
                    setattr(namer_config, name, new_value)

    if not hasattr(namer_config, 'retry_time') or namer_config.retry_time is None:
        setattr(namer_config, 'retry_time', f'03:{random.randint(0, 59):0>2}')  # noqa: B010

    return namer_config


def resource_file_to_str(package: str, file_name: str) -> str:
    config_str = ''
    if hasattr(resources, 'files'):
        config_str = resources.files(package).joinpath(file_name).read_text(encoding='UTF-8')
    elif hasattr(resources, 'read_text'):
        config_str = resources.read_text(package, file_name)

    return config_str


def copy_resource_to_file(package: str, file_name: str, output: Path) -> bool:
    if hasattr(resources, 'files'):
        with resources.files(package).joinpath(file_name).open('rb') as _bin, open(output, mode='+bw') as out:
            shutil.copyfileobj(_bin, out)
            return True
    elif hasattr(resources, 'read_text'):
        with resources.open_binary(package, file_name) as _bin, open(output, mode='+bw') as out:
            shutil.copyfileobj(_bin, out)
            return True

    return False


def default_config(user_set: Optional[Path] = None) -> NamerConfig:
    """
    Attempts reading various locations to fine a namer.cfg file.
    """
    config = ConfigUpdater(allow_no_value=True)
    config_str = resource_file_to_str('namer', 'namer.cfg.default')
    config.read_string(config_str)
    namer_config = from_config(config, NamerConfig())
    namer_config.config_updater = config

    user_config = ConfigUpdater(allow_no_value=True)
    cfg_paths = [
        user_set,
        os.environ.get('NAMER_CONFIG'),
        Path.home() / '.namer.cfg',
        '.namer.cfg',
    ]

    for file in cfg_paths:
        if not file:
            continue

        if isinstance(file, str):
            file = Path(file)

        if file.is_file():
            user_config.read(file, encoding='UTF-8')
            break

    return from_config(user_config, namer_config)
