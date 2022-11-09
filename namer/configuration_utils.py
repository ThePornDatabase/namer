"""
Namer Configuration readers/verifier
"""

import json
import os
import io
import random
import re
import tempfile
from typing import Dict, List, Optional, Callable, Pattern, Any, Tuple
from configupdater import ConfigUpdater
from datetime import timedelta
from pathlib import Path

from loguru import logger
from requests_cache import BACKEND_CLASSES, BaseCache, CachedSession

from namer.configuration import NamerConfig
from namer.database import abbreviations
from namer.name_formatter import PartialFormatter


def __verify_naming_config(config: NamerConfig, formatter: PartialFormatter) -> bool:
    """
    Verifies the contents of your config file. Returns False if configuration failed.
    """
    success = True
    if not config.enable_metadataapi_genres and not config.default_genre:
        logger.error("Since enable_metadataapi_genres is not True, you must specify a default_genre")
        success = False
    success = __verify_name_string(formatter, "inplace_name", config.inplace_name) and success
    return success


def __verify_watchdog_config(config: NamerConfig, formatter: PartialFormatter) -> bool:
    """
    Verifies the contents of your config file. Returns False if configuration failed.
    """
    success = True
    if not config.enable_metadataapi_genres and not config.default_genre:
        logger.error("Since enable_metadataapi_genres is not True, you must specify a default_genre")
        success = False
    success = __verify_dir(config, "watch_dir") and success
    success = __verify_dir(config, "work_dir") and success
    success = __verify_dir(config, "failed_dir") and success
    success = __verify_dir(config, "dest_dir") and success
    success = __verify_name_string(formatter, "new_relative_path_name", config.new_relative_path_name) and success
    return success


def __verify_dir(config: NamerConfig, name: str) -> bool:
    """
    verify a config directory exist. return false if verification fails
    """
    file_name = getattr(config, name) if hasattr(config, name) else None
    if file_name and not file_name.is_dir():
        logger.error("Configured directory {}: {} is not a directory or not accessible", name, file_name)
        return False

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
        logger.error("Configuration {} is not a valid file name format, please check {}", name, name_string)
        logger.error("Error message: {}", key_error)
        return False


def verify_configuration(config: NamerConfig, formatter: PartialFormatter) -> bool:
    """
    Can verify a NamerConfig with a formatter
    """
    success = __verify_naming_config(config, formatter)
    success = __verify_watchdog_config(config, formatter) and success
    return success


def get_str(updater: ConfigUpdater, section: str, key: str) -> Optional[str]:
    if updater.has_option(section, key):
        output = updater.get(section, key)
        return str(output.value)
    else:
        return None
        # raise RuntimeError(f"Not a configuration section: {section} key: {key}")


def to_bool(value: Optional[str]) -> Optional[bool]:
    return value.lower() == "true" if value else None


def from_bool(value: Optional[bool]) -> str:
    return str(value) if value is not None else ""


def to_str_list_lower(value: Optional[str]) -> List[str]:
    return [x.strip().lower() for x in value.lower().split(',')] if value else []


def from_str_list_lower(value: Optional[List[str]]) -> str:
    return ", ".join(value) if value else ""


def to_int(value: Optional[str]) -> Optional[int]:
    return int(value) if value else None


def from_int(value: Optional[int]) -> str:
    return str(value) if value else ""


def to_path(value: Optional[str]) -> Optional[Path]:
    return Path(value).resolve() if value else None


def from_path(value: Optional[Path]) -> str:
    return str(value) if value else ""


def to_regex_list(value: Optional[str]) -> List[Pattern]:
    return [re.compile(x.strip()) for x in value.split(',')] if value else []


def from_regex_list(value: Optional[List[Pattern]]) -> str:
    return ", ".join([x.pattern for x in value]) if value else ""


def to_site_abreviation(site_abbreviations: Optional[str]) -> Dict[Pattern, str]:
    abbreviations_db = abbreviations.copy()
    if site_abbreviations:
        data = json.loads(site_abbreviations)
        abbreviations_db.update(data)
    new_abbreviation: Dict[Pattern, str] = {}
    for abbreviation, full in abbreviations_db.items():
        key = re.compile(fr'^{abbreviation}[ .-]+', re.IGNORECASE)
        new_abbreviation[key] = f'{full} '
    return new_abbreviation


def from_site_abreviation(site_abbreviations: Optional[Dict[Pattern, str]]) -> str:
    out: Dict[str, str] = {x.pattern[1:-6]: y[0:-1] for (x, y) in site_abbreviations.items()} if site_abbreviations else {}
    wrapper = io.StringIO("")
    json.dump(out, wrapper)
    return wrapper.getvalue()


def to_pattern(value: Optional[str]) -> Optional[Pattern]:
    return re.compile(value, re.IGNORECASE) if value else None


def from_pattern(value: Optional[Pattern]) -> str:
    return value.pattern if value else ""


def to_site_list(value: Optional[str]) -> List[str]:
    return [re.sub(r"[^a-z0-9]", "", x.strip().lower()) for x in value.split(",")] if value else []


def set_str(updater: ConfigUpdater, section: str, key: str, value: str) -> None:
    updater[section][key].value = value


def set_comma_list(updater: ConfigUpdater, section: str, key: str, value: List[str]) -> None:
    updater[section][key].value = ", ".join(value)


def set_int(updater: ConfigUpdater, section: str, key: str, value: int) -> None:
    updater[section][key].value = str(value)


def set_boolean(updater: ConfigUpdater, section: str, key: str, value: bool) -> None:
    updater[section][key] = str(value)


field_info: Dict[str, Tuple[str, Optional[Callable[[Optional[str]], Any]], Optional[Callable[[Any], str]]]] = {
    "porndb_token": ("namer", None, None),
    "name_parser": ("namer", None, None),
    "inplace_name": ("namer", None, None),
    "prefer_dir_name_if_available": ("namer", to_bool, from_bool),
    "min_file_size": ("namer", to_int, from_int),
    "write_namer_log": ("namer", to_bool, from_bool),
    "write_namer_failed_log": ("namer", to_bool, from_bool),
    "target_extensions": ("namer", to_str_list_lower, from_str_list_lower),
    "update_permissions_ownership": ("namer", to_bool, from_bool),
    "set_dir_permissions": ("namer", to_int, from_int),
    "set_file_permissions": ("namer", to_int, from_int),
    "set_uid": ("namer", to_int, from_int),
    "set_gid": ("namer", to_int, from_int),
    "trailer_location": ("namer", None, None),
    "sites_with_no_date_info": ("namer", to_str_list_lower, from_str_list_lower),
    "movie_data_prefered": ("namer", to_str_list_lower, from_str_list_lower),
    "vr_studios": ("namer", to_str_list_lower, from_str_list_lower),
    "vr_tags": ("namer", to_str_list_lower, from_str_list_lower),
    "site_abbreviations": ("namer", to_site_abreviation, from_site_abreviation),
    "max_performer_names": ("namer", to_int, from_int),
    "use_requests_cache": ("namer", to_bool, from_bool),
    "requests_cache_expire_minutes": ("namer", to_int, from_int),
    "override_tpdb_address": ("namer", to_bool, from_bool),
    "search_phash": ("Phash", to_bool, from_bool),
    "require_match_phash_top": ("Phash", to_bool, from_bool),
    "send_phash_of_matches_to_tpdb": ("Phash", to_bool, from_bool),
    "write_nfo": ("metadata", to_bool, from_bool),
    "enabled_tagging": ("metadata", to_bool, from_bool),
    "enabled_poster": ("metadata", to_bool, from_bool),
    "enable_metadataapi_genres": ("metadata", to_bool, from_bool),
    "default_genre": ("metadata", None, None),
    "language": ("metadata", None, None),
    "preserve_duplicates": ("duplicates", to_bool, from_bool),
    "max_desired_resolutions": ("duplicates", to_int, from_int),
    "desired_codec": ("duplicates", to_str_list_lower, from_str_list_lower),
    "ignored_dir_regex": ("watchdog", to_pattern, from_pattern),
    "del_other_files": ("watchdog", to_bool, from_bool),
    "extra_sleep_time": ("watchdog", to_int, from_int),
    "new_relative_path_name": ("watchdog", None, None),
    "watch_dir": ("watchdog", to_path, from_path),
    "work_dir": ("watchdog", to_path, from_path),
    "failed_dir": ("watchdog", to_path, from_path),
    "dest_dir": ("watchdog", to_path, from_path),
    "retry_time": ("watchdog", None, None),
    "web": ("watchdog", to_bool, from_bool),
    "port": ("watchdog", to_int, from_int),
    "host": ("watchdog", None, None),
    "web_root": ("watchdog", None, None),
    "allow_delete_files": ("watchdog", to_bool, from_bool),
    "add_max_percent_column": ("watchdog", to_bool, from_bool),
    "debug": ("watchdog", to_bool, from_bool),
    "diagnose_errors": ("watchdog", to_bool, from_bool),
}


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

    if not hasattr(namer_config, "retry_time") or namer_config.retry_time is None:
        setattr(namer_config, "retry_time", f"03:{random.randint(0, 59):0>2}")

    # create a CachedSession objects for request caching.
    if namer_config.enabled_requests_cache:
        cache_file = Path(tempfile.gettempdir()) / "namer_cache"
        sqlite_supported = issubclass(BACKEND_CLASSES['sqlite'], BaseCache)
        backend = 'sqlite' if sqlite_supported else 'filesystem'
        expire_time = timedelta(minutes=namer_config.requests_cache_expire_minutes)
        namer_config.cache_session = CachedSession(str(cache_file), backend=backend, expire_after=expire_time, ignored_parameters=["Authorization"])

    return namer_config


def default_config() -> NamerConfig:
    """
    Attempts reading various locations to fine a namer.cfg file.
    """
    config = ConfigUpdater()
    config.read("namer.cfg.default")
    namer_config = from_config(config, NamerConfig())
    namer_config.config_updater = config

    user_config = ConfigUpdater()
    config_loc = os.environ.get("NAMER_CONFIG")
    if config_loc and Path(config_loc).exists():
        user_config.read(config_loc)
    elif (Path.home() / ".namer.cfg").exists():
        user_config.read(str(Path.home() / ".namer.cfg"))
    elif Path("./namer.cfg").exists():
        user_config.read(".namer.cfg")
    user_config.read("namer.cfg.default")
    return from_config(user_config, namer_config)
