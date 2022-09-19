"""
Namer Configuration readers/verifier
"""

import configparser
import json
import os
import random
import re
import tempfile
from configparser import ConfigParser
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


def from_config(config: ConfigParser) -> NamerConfig:
    """
    Given a config parser pointed at a namer.cfg file, return a NamerConfig with the file's parameters.
    """
    namer_config = NamerConfig()
    namer_config.porndb_token = config.get("namer", "porndb_token", fallback="")
    namer_config.inplace_name = config.get("namer", "inplace_name", fallback="{site} - {date} - {name}.{ext}")
    namer_config.name_parser = config.get("namer", "name_parser", fallback="{_site}{_sep}{_optional_date}{_ts}{_name}{_dot}{_ext}")
    namer_config.prefer_dir_name_if_available = config.getboolean("namer", "prefer_dir_name_if_available", fallback=False)
    namer_config.target_extensions = [x.strip().lower() for x in config.get("namer", "target_extensions", fallback="mp4,mkv,avi,mov,flv").split(",")]

    namer_config.min_file_size = config.getint("namer", "min_file_size", fallback=100)
    namer_config.set_uid = config.getint("namer", "set_uid", fallback=None)
    namer_config.set_gid = config.getint("namer", "set_gid", fallback=None)
    namer_config.trailer_location = config.get("namer", "trailer_location", fallback=None)
    namer_config.sites_with_no_date_info = [re.sub(r"[^a-z0-9]", "", x.strip().lower()) for x in config.get("namer", "sites_with_no_date_info", fallback="").split(",")]
    if "" in namer_config.sites_with_no_date_info:
        namer_config.sites_with_no_date_info.remove("")

    abbreviations_db = abbreviations.copy()
    site_abbreviations = config.get("namer", "site_abbreviations", fallback=None)
    if site_abbreviations:
        data = json.loads(site_abbreviations)
        abbreviations_db.update(data)

    new_abbreviation = {}
    for abbreviation, full in abbreviations_db.items():
        key = re.compile(fr'^{abbreviation}[ .-]+', re.IGNORECASE)
        new_abbreviation[key] = f'{full} '

    namer_config.site_abbreviations = new_abbreviation

    namer_config.override_tpdb_address = config.get("namer", "override_tpdb_address", fallback="https://api.metadataapi.net/")

    namer_config.write_namer_log = config.getboolean("namer", "write_namer_log", fallback=False)
    namer_config.write_namer_failed_log = config.getboolean("namer", "write_namer_failed_log", fallback=True)
    namer_config.update_permissions_ownership = config.getboolean("namer", "update_permissions_ownership", fallback=False)
    namer_config.set_dir_permissions = config.getint("namer", "set_dir_permissions", fallback=775)
    namer_config.set_file_permissions = config.getint("namer", "set_file_permissions", fallback=664)
    namer_config.max_performer_names = config.getint("namer", "max_performer_names", fallback=6)
    namer_config.enabled_requests_cache = config.getboolean("namer", "use_requests_cache", fallback=True)
    namer_config.requests_cache_expire_minutes = config.getint("namer", "requests_cache_expire_minutes", fallback=10)

    namer_config.movie_data_prefered = [x.strip().upper() for x in config.get("namer", "movie_data_prefered", fallback="").split(",")]
    vr_studios = "18 VR,Babe VR,Badoink VR,Dorm Room,Kink VR,Real VR,RealJamVR,Sex Like Real,SexBabesVR,SinsVR,SLR Originals,Swallowbay,Virtual Taboo,VirtualRealPorn,VR Bangers,VR Cosplay X,VR Hush,VRConk,VRedging,Wankz VR"
    namer_config.vr_studios = [x.strip().upper() for x in config.get("namer", "vr_studios", fallback=vr_studios).split(",")]
    namer_config.vr_tags = [x.strip().upper() for x in config.get("namer", "vr_tags", fallback="virtual reality, vr porn").split(",")]

    namer_config.preserve_duplicates = config.getboolean("duplicates", "preserve_duplicates", fallback=True)
    namer_config.max_desired_resolutions = config.getint("duplicates", "max_desired_resolutions", fallback=-1)
    namer_config.desired_codec = [x.strip().upper() for x in config.get("duplicates", "desired_codec", fallback="hevc,h264").split(",")]

    namer_config.write_nfo = config.getboolean("metadata", "write_nfo", fallback=False)
    namer_config.enabled_tagging = config.getboolean("metadata", "enabled_tagging", fallback=True)
    namer_config.enabled_poster = config.getboolean("metadata", "enabled_poster", fallback=True)
    namer_config.enable_metadataapi_genres = config.getboolean("metadata", "enable_metadataapi_genres", fallback=False)
    namer_config.default_genre = config.get("metadata", "default_genre", fallback="Adult")
    namer_config.language = config.get("metadata", "language", fallback=None)
    namer_config.ignored_dir_regex = config.get("metadata", "ignored_dir_regex", fallback=".*_UNPACK_.*")
    namer_config.new_relative_path_name = config.get("watchdog", "new_relative_path_name", fallback="{site} - {date} - {name}/{site} - {date} - {name}.{ext}")
    namer_config.del_other_files = config.getboolean("watchdog", "del_other_files", fallback=False)
    namer_config.extra_sleep_time = config.getint("watchdog", "extra_sleep_time", fallback=30)

    watch_dir = config.get("watchdog", "watch_dir", fallback=None)
    if watch_dir:
        namer_config.watch_dir = Path(watch_dir).resolve()

    work_dir = config.get("watchdog", "work_dir", fallback=None)
    if work_dir:
        namer_config.work_dir = Path(work_dir).resolve()

    failed_dir = config.get("watchdog", "failed_dir", fallback=None)
    if failed_dir:
        namer_config.failed_dir = Path(failed_dir).resolve()

    dest_dir = config.get("watchdog", "dest_dir", fallback=None)
    if dest_dir:
        namer_config.dest_dir = Path(dest_dir).resolve()

    namer_config.retry_time = config.get("watchdog", "retry_time", fallback=f"03:{random.randint(0, 59):0>2}")
    namer_config.web = config.getboolean("watchdog", "web", fallback=False)
    namer_config.port = config.getint("watchdog", "port", fallback=6980)
    namer_config.host = config.get("watchdog", "host", fallback="0.0.0.0")
    namer_config.web_root = config.get("watchdog", "web_root", fallback=None)
    namer_config.allow_delete_files = config.getboolean("watchdog", "allow_delete_files", fallback=False)
    namer_config.diagnose_errors = config.getboolean("watchdog", "diagnose_errors", fallback=False)

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
    config = configparser.ConfigParser()
    default_locations = []
    config_loc = os.environ.get("NAMER_CONFIG")
    if config_loc and Path(config_loc).exists():
        default_locations = [Path(config_loc)]
    elif (Path.home() / ".namer.cfg").exists():
        default_locations = [Path.home() / ".namer.cfg"]
    elif Path("./namer.cfg").exists():
        default_locations = [Path("./namer.cfg")]
    config.read(default_locations)
    return from_config(config)
