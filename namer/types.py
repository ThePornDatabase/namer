"""
Types shared by all the files in this project, used as interfaces for moving data.
"""

import configparser
import os
import random
import re
import string
import sys
import tempfile
from configparser import ConfigParser
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path, PurePath
from typing import List, Optional, Sequence

from requests_cache import CachedSession
from loguru import logger
from pathvalidate import Platform, sanitize_filename


def _verify_name_string(name: str, name_string: str) -> bool:
    """
    Verify the name format string.
    """
    info = LookedUpFileInfo()
    try:
        formatter = PartialFormatter()
        formatter.format(name_string, **info.as_dict())
        return True
    except KeyError as key_error:
        logger.error("Configuration {} is not a valid file name format, please check {}", name, name_string)
        logger.error("Error message: {}", key_error)
        return False


class PartialFormatter(string.Formatter):
    """
    Used for formatting NamerConfig.inplace_name and NamerConfig.
    """

    supported_keys = [
        "date",
        "description",
        "name",
        "site",
        "full_site",
        "performers",
        "all_performers",
        "act",
        "ext",
        "trans",
    ]

    def __init__(self, missing="~~", bad_fmt="!!"):
        self.missing, self.bad_fmt = missing, bad_fmt

    def get_field(self, field_name, args, kwargs):
        # Handle a key not found
        try:
            val = super().get_field(field_name, args, kwargs)
        except (KeyError, AttributeError) as err:
            val = None, field_name
            if field_name not in self.supported_keys:
                raise KeyError(f"Key {field_name} not in support keys: {self.supported_keys}") from err
        return val

    def format_field(self, value, format_spec: str):
        if value is None:
            return self.missing
        try:
            if re.match(r".\d+s", format_spec):
                value = value + format_spec[0] * int(format_spec[1:-1])
                format_spec = ""
            if re.match(r".\d+p", format_spec):
                value = format_spec[0] * int(format_spec[1:-1]) + value
                format_spec = ""
            if re.match(r".\d+i", format_spec):
                value = format_spec[0] * int(format_spec[1:-1]) + value + format_spec[0] * int(format_spec[1:-1])
                format_spec = ""
            return super().format_field(value, format_spec)
        except ValueError:
            if self.bad_fmt is not None:
                return self.bad_fmt
            raise


# noinspection PyDataclass
@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class NamerConfig:
    """
    Configuration for namer and namer_watchdog
    """

    # pylint: disable=too-many-instance-attributes

    porndb_token: str
    """
    token to access porndb.
    sign up here: https://metadataapi.net/
    """

    name_parser: str = "{_site}{_optional_date}{_sep}{_ts}{_name}{_dot}{_ext}"
    """
    This config may be a regex you provide, or a set of token used to build a regex.

    By default names are of the form:
    ``Site.YYYY.MM.DD.TS.scene.name.mkv``,``Site.YYYY.MM.DD.scene.name.mkv``,``Site.TS.scene.name.mkv``,``Site.scene.name.mkv``

     Supported token:
    ```
    _sep            r'[\\.\\- ]+'
    _site           r'(?P<site>[a-zA-Z0-9\\.\\-\\ ]*?[a-zA-Z0-9]*?)'
    _date           r'(?P<year>[0-9]{2}(?:[0-9]{2})?)[\\.\\- ]+(?P<month>[0-9]{2})[\\.\\- ]+(?P<day>[0-9]{2})'
    _optional_date  r'(?:(?P<year>[0-9]{2}(?:[0-9]{2})?)[\\.\\- ]+(?P<month>[0-9]{2})[\\.\\- ]+(?P<day>[0-9]{2})[\\.\\- ]+)?'
    _ts             r'((?P<trans>[T|t][S|s])'+_sep+'){0,1}'
    _name           r'(?P<name>(?:.(?![0-9]{2,4}[\\.\\- ][0-9]{2}[\\.\\- ][0-9]{2}))*)'
    _dot            r'\\.'
    _ext            r'(?P<ext>[a-zA-Z0-9]{3,4})$'
    ```

    The parts extracted from the file will be used in matching.
    _ts  is optional, and is mostly useful in stripping the marker from the _name, aiding in matching.
    _date if present is used to ensure the match is within 24 hours of your date.
    If the year/month/day capture groups are not present (due to you not using the supplied _date regex)
    dates will not be used in matching, possibly allowing false positives.
    """

    inplace_name: str = "{site} - {date} - {name}.{ext}"
    """
    How to write output file name.  When namer.py is run this is applied in place
    (next to the file to be processed).
    When run from namer_watchdog.py this will be written in to the success dir.

    Supports stand python 3 formatting, as well as:
    * a prefix:
    {site: 1p} - in this case put one space in front of the 'site', so ' Vixen'
    * a suffix:
    {date:_1s} - in this case put one underscore after the 'date', so '2020-01-01_'
    * an infix:
    {date:_2i} - in this case put two underscore before and after the 'date', so '__2020-01-01__'

    Examples:
    * {site} - {date} - {scene}.{ext}
    * {site}/{date}.{scene}.{ext}

    Missing values will be ignored.

    Allowed replacements:

    * 'date' - in the format of YYYY-MM-DD.
    * 'description' - too long, don't use in a name.
    * 'name' - the scene name
    * 'site' - the site name, BrazzersExxtra, AllHerLuv, Deeper, etc with spaces removed.
    * 'full_site' - the site name from porndb, unmodified, i.e: Brazzers Exxtra, All Her Luv, etc.
    * 'performers' - space seperated list of female performers
    * 'all_performers' - space seperated list of all performers
    * 'act' - an act, parsed from original file name, don't use.
    * 'ext' - original file's extension, you should keep this.
    * 'trans' - 'TS', or 'ts' if detected in original file name.

    """

    min_file_size: int = 300
    """
    minimum file size to process in MB, ignored if a file is to be processed
    """

    prefer_dir_name_if_available: bool = True
    """
    If a directory name is to be preferred over a file name.
    """

    target_extensions: List[str]
    """
    File types namer targets, only 'mp4's can be tagged, others can be renamed.
    """

    write_namer_log: bool = False
    """
    Should a log of comparisons be written next to processed video files.
    """

    update_permissions_ownership: bool = False
    """
    Should file permissions/ownership be updated.
    If false, set_uid/set_gid,set_dir_permissions,set_file_permissions will be ignored
    """

    set_uid: Optional[int] = None
    """
    UID Settings for new/moved files/dirs.
    """

    set_gid: Optional[int] = None
    """
    GID Settings for new/moved files/dirs.
    """

    set_dir_permissions: Optional[int] = 775
    """
    Permissions Settings for new/moved dirs.
    """

    set_file_permissions: Optional[int] = 664
    """
    Permissions Settings for new/moved file.
    """

    max_performer_names: int = 6
    """
    When guessing at matches namer can use performer names to attempt to match.   This can be costly in terms of cpu time.
    Plus who lists all the performers if over 6 on a scene's name?   You can increase this, but the cpu/runtime cost increases
    rapidly (combinatorial)
    """

    write_nfo: bool = False
    """
    Write an nfo file next to the directory in an emby/jellyfin readable format.
    """

    trailer_location: Optional[str] = None
    """
    If you want the trailers downloaded set the value relative to the final location of the movie file here.
    Plex:      Trailers/trailer.{ext}, or extras/Trailer-trailer.{ext}
    Jellyfin:  trailer/trailer.{ext}
    Extensions are handled by the download's mime type.
    Leave empty to not download trailers.
    """

    sites_with_no_date_info: Sequence[str]
    """
    A list of site names that do not have proper date information in them.   This is a problem with some tpdb
    scrapers/storage mechanisms.
    """

    enabled_requests_cache: bool = True
    """
    Cache http requests
    """

    requests_cache_expire_minutes: int = 10
    """
    Amount of minutes that http request would be in cache
    """

    enabled_tagging: bool = True
    """
    Currently metadata pulled from the porndb can be added to mp4 files.
    This metadata will be read in fully by Plex, and Apple TV app, partially by Jellyfin (no artist support).
    Metadata includes, Title, Release Date, Scene Name, Artist, Source URL, XXX Movie rating.
    If a file is an mkv adding metadata at this time isn't supported.

    Should metadata fetched from the porn db be written in to the metadata of the mp4.
    No flags in this section will be used if this is not set to true.
    """

    enabled_poster: bool = True
    """
    Should the poster fetched from the porn db be written in to the metadata of the mp4.
    This poster will be displayed in Plex, Jellyfin and Apple TV app.
    Only applicable if enabled_tagging is True
    """

    enable_metadataapi_genres: bool = False
    """
    Should genres pulled from the porndb be added to the file?   These genres are noisy and
    not recommend for use.  If this is false a single default genre will be used.
    """

    default_genre: str = "Adult"
    """
    If genre's are not copied this is the default genre added to files.
    Default value is adult.
    """

    language: Optional[str] = None
    """
    if language is set it will be used to select the default audio stream in an mp4 that has too many default stream
    to play correct in quicktime/apple tv.   If the language isn't found or is already the only default no action is
    taken, no streams (audio/video) are re-encoded.  Available here: https://iso639-3.sil.org/code_tables/639/data/
    """

    ignored_dir_regex: str = ".*_UNPACK_.*"
    """
    If a file found in the watch dir matches this regex it will be ignored, useful for some file processes.
    """

    new_relative_path_name: str = "{site} - {date} - {name}/{site} - {date} - {name}.{ext}"
    """
    like inplace_name above used for local call for renaming, this instead is used to move a file/dir to a location relative
    to the dest_dir below on successful matching/tagging.
    """

    del_other_files: bool = False
    """
    when processing a directory in the dest dir, should extra files besides the largest video be removed?
    or attempt to move them to a subdirectory specified in new_relative_path_name, if one exist.
    """

    watch_dir: Path
    """
    If running in watchdog mode, director where new downloads go.
    """

    work_dir: Path
    """
    If running in watchdog mode, temporary directory where work is done.
    a log file shows attempted matches and match closeness.
    """

    failed_dir: Path
    """
    If running in watchdog mode, Should processing fail the file or directory is moved here.
    Files can be manually moved to watch-dir to force reprocessing.
    """

    dest_dir: Path
    """
    If running in watchdog mode, dir where finalized files get written.
    """

    retry_time: str
    """
    Time to retry failed items every day.
    """

    extra_sleep_time: int = 30
    """
    Extra time to sleep in seconds to allow all information to be copied in dir
    """

    web: bool = True
    """
    Run webserver while running watchdog
    """

    port: int = 6980
    """
    Web server port
    """

    host: str = "0.0.0.0"
    """
    Web server host
    """

    web_root: Optional[str] = None
    """
    webroot (root url to place pages), useful for reverse proxies
    """

    allow_delete_files: bool = False
    """
    Allow to delete files in web interface
    """

    cache_session: Optional[CachedSession]
    """
    If enabled_requests_cache is true this http.session will be constructed and used for requests to tpdb.
    """

    def __init__(self):
        if sys.platform != "win32":
            self.set_uid = os.getuid()
            self.set_gid = os.getgid()

    def __str__(self):
        token = "None In Set, Go to https://metadatapi.net/ to get one!"
        if self.porndb_token is not None:
            token = "*" * len(self.porndb_token)
        output = "Namer Config:\n"
        output += f"  porndb_token: {token}\n"
        output += f"  inplace_name: {self.inplace_name}\n"
        output += f"  prefer_dir_name_if_available: {self.prefer_dir_name_if_available}\n"
        output += f"  target_extensions: {self.target_extensions}\n"
        output += f"  write_namer_log: {self.write_namer_log}\n"
        output += f"  trailer_location: {self.trailer_location}\n"
        output += f"  sites_with_no_date_info: {self.sites_with_no_date_info}\n"
        output += f"  update_permissions_ownership: {self.update_permissions_ownership}\n"
        output += f"  set_dir_permissions: {self.set_dir_permissions}\n"
        output += f"  set_file_permissions: {self.set_file_permissions}\n"
        output += f"  set_uid: {self.set_file_permissions}\n"
        output += f"  set_gid: {self.set_file_permissions}\n"
        output += f"  max_performer_names: {self.set_file_permissions}\n"
        output += f"  enabled_requests_cache: {self.enabled_requests_cache}\n"
        output += f"  requests_cache_expire_minutes: {self.requests_cache_expire_minutes}\n"
        output += "Tagging Config:\n"
        output += f"  write_nfo: {self.write_nfo}\n"
        output += f"  enabled_tagging: {self.enabled_tagging}\n"
        output += f"  enabled_poster: {self.enabled_poster}\n"
        output += f"  enable_metadataapi_genres: {self.enable_metadataapi_genres}\n"
        output += f"  default_genre: {self.default_genre}\n"
        output += f"  language: {self.language}\n"
        output += "Watchdog Config:\n"
        output += f"  ignored_dir_regex: {self.ignored_dir_regex}\n"
        output += f"  min_file_size: {self.min_file_size}mb\n"
        output += f"  del_other_files: {self.del_other_files}\n"
        output += f"  new_relative_path_name: {self.new_relative_path_name}\n"
        output += f"  watch_dir: {self.watch_dir}\n"
        output += f"  work_dir: {self.work_dir}\n"
        output += f"  failed_dir: {self.failed_dir}\n"
        output += f"  dest_dir: {self.dest_dir}\n"
        output += f"  retry_time: {self.retry_time}\n"
        output += f"  extra_sleep_time: {self.extra_sleep_time}\n"
        output += f"  web: {self.web}\n"
        output += f"  port: {self.port}\n"
        output += f"  host: {self.host}\n"
        output += f"  web_root: {self.web_root}\n"
        output += f"  allow_delete_files: {self.allow_delete_files}\n"
        return output

    def verify_naming_config(self) -> bool:
        """
        Verifies the contents of your config file. Returns False if configuration failed.
        """
        success = True
        if self.enable_metadataapi_genres is not True and self.default_genre is None:
            logger.error("Since enable_metadataapi_genres is not True, you must specify a default_genre")
            success = False
        success = _verify_name_string("inplace_name", self.inplace_name) and success
        return success

    def verify_watchdog_config(self) -> bool:
        """
        Verifies the contents of your config file. Returns False if configuration failed.
        """
        success = True
        if self.enable_metadataapi_genres is not True and self.default_genre is None:
            logger.error("Since enable_metadataapi_genres is not True, you must specify a default_genre")
            success = False
        success = self._verify_dir("watch_dir") and success
        success = self._verify_dir("work_dir") and success
        success = self._verify_dir("failed_dir") and success
        success = self._verify_dir("dest_dir") and success
        success = _verify_name_string("new_relative_path_name", self.new_relative_path_name) and success
        return success

    def _verify_dir(self, name: str) -> bool:
        """
        verify a config directory exist. return false if verification fails
        """
        file_name = getattr(self, name) if hasattr(self, name) else None
        if file_name is not None and not file_name.is_dir():
            logger.error("Configured directory {}: {} is not a directory or not accessible", name, file_name)
            return False
        return True


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

    namer_config.write_namer_log = config.getboolean("namer", "write_namer_log", fallback=False)
    namer_config.update_permissions_ownership = config.getboolean("namer", "update_permissions_ownership", fallback=False)
    namer_config.set_dir_permissions = config.getint("namer", "set_dir_permissions", fallback=775)
    namer_config.set_file_permissions = config.getint("namer", "set_file_permissions", fallback=664)
    namer_config.max_performer_names = config.getint("namer", "max_performer_names", fallback=6)
    namer_config.enabled_requests_cache = config.getboolean("namer", "use_requests_cache", fallback=True)
    namer_config.requests_cache_expire_minutes = config.getint("namer", "requests_cache_expire_minutes", fallback=10)
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
    if watch_dir is not None:
        namer_config.watch_dir = Path(watch_dir).resolve()
    work_dir = config.get("watchdog", "work_dir", fallback=None)
    if work_dir is not None:
        namer_config.work_dir = Path(work_dir).resolve()
    failed_dir = config.get("watchdog", "failed_dir", fallback=None)
    if failed_dir is not None:
        namer_config.failed_dir = Path(failed_dir).resolve()
    dest_dir = config.get("watchdog", "dest_dir", fallback=None)
    if dest_dir is not None:
        namer_config.dest_dir = Path(dest_dir).resolve()
    namer_config.retry_time = config.get("watchdog", "retry_time", fallback=f"03:{random.randint(0, 59):0>2}")
    namer_config.web = config.getboolean("watchdog", "web", fallback=False)
    namer_config.port = config.getint("watchdog", "port", fallback=6980)
    namer_config.host = config.get("watchdog", "host", fallback="0.0.0.0")
    namer_config.web_root = config.get("watchdog", "web_root", fallback=None)
    namer_config.allow_delete_files = config.getboolean("watchdog", "allow_delete_files", fallback=False)

    # create a CachedSession objects for request caching.
    if namer_config.enabled_requests_cache:
        cache_file = Path(tempfile.gettempdir()) / "namer_cache"
        expire_time = timedelta(minutes=namer_config.requests_cache_expire_minutes)
        namer_config.cache_session = CachedSession(str(cache_file), backend='filesystem', expire_after=expire_time, ignored_parameters=["Authorization"])
    return namer_config


def default_config() -> NamerConfig:
    """
    Attempts reading various locations to fine a namer.cfg file.
    """
    config = configparser.ConfigParser()
    default_locations = []
    config_loc = os.environ.get("NAMER_CONFIG")
    if config_loc is not None and Path(config_loc).exists():
        default_locations = [Path(config_loc)]
    elif (Path.home() / ".namer.cfg").exists():
        default_locations = [Path.home() / ".namer.cfg"]
    elif Path("./namer.cfg").exists():
        default_locations = [Path("./namer.cfg")]
    config.read(default_locations)
    return from_config(config)


@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class FileNameParts:
    """
    Represents info parsed from a file name, usually of a nzb, named something like:
    'EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.2160p.MP4-GAYME-xpost'
    or
    'DorcelClub.20.12..Aya.Benetti.Megane.Lopez.And.Bella.Tina.2160p.MP4-GAYME-xpost'
    """

    # pylint: disable=too-many-instance-attributes

    site: Optional[str] = None
    """
    Site the file originated from, "DorcelClub", "EvilAngel", etc.
    """
    date: Optional[str] = None
    """
    formatted: YYYY-mm-dd
    """
    trans: bool = False
    """
    If the name originally started with an "TS" or "ts"
    it will be stripped out and placed in a separate location, aids in matching, usable to genre mark content.
    """
    name: Optional[str] = None
    """
    The remained of a file, usually between the date and video markers such as XXX, 4k, etc.   Heavy lifting
    occurs to match this to a scene name, perform names, or a combo of both.
    """
    extension: Optional[str] = None
    """
    The file's extension .mp4 or .mkv
    """
    source_file_name: Optional[str] = None
    """
    What was originally parsed.
    """

    def __str__(self) -> str:
        return f"""site: {self.site}
        date: {self.date}
        trans: {self.trans}
        name: {self.name}
        extension: {self.extension}
        original full name: {self.source_file_name}
        """


@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class Performer:
    """
    Minimal info about a performer, name, and role.
    """

    name: str
    role: str
    image: Optional[str]
    """
    if available the performers gender, stored as a role.  example: "Female", "Male"
    Useful as many nzbs often don't include the scene name, but instead female performers names,
    or sometimes both.
    Other performers are also used in name matching, if females are attempted first.
    """

    def __init__(self, name=None, role=None, image=None):
        self.name = name
        self.role = role
        self.image = image

    def __str__(self):
        name = "Unknown" if self.name is None else self.name
        if self.role is not None:
            return name + " (" + self.role + ")"
        return name

    def __repr__(self):
        return f"Performer[name={self.name}, role={self.role}, image={self.image}]"


# noinspection PyDataclass
@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class LookedUpFileInfo:
    """
    Information from a call to the porndb about a specific scene.
    """

    # pylint: disable=too-many-instance-attributes

    uuid: Optional[str] = None
    """
    porndb scene id, allowing lookup of more metadata, (tags)
    """

    site: Optional[str] = None
    """
    Site where this video originated, DorcelClub/Deeper/etc.....
    """
    date: Optional[str] = None
    """
    date of initial release, formatted YYYY-mm-dd
    """
    name: Optional[str] = None
    """
    Name of the scene in this video
    """
    description: Optional[str] = None
    """
    Description of the action in this video
    """
    source_url: Optional[str] = None
    """
    Original source location of this video
    """
    poster_url: Optional[str] = None
    """
    Url to download a poster for this video
    """
    performers: List[Performer]
    """
    List of performers, containing names, and "roles" aka genders, for each performer.
    """
    genres: List[str]
    """
    List of genres, per porndb.  Tends to be noisy.
    """
    original_response: Optional[str] = None
    """
    json response parsed in to this object.
    """
    original_query: Optional[str] = None
    """
    url query used to get the above json response
    """
    original_parsed_filename: Optional[FileNameParts]
    """
    The FileNameParts used to build the original_query
    """
    look_up_site_id: Optional[str] = None
    """
    ID Used by the queried site to identify the video
    """
    trailer_url: Optional[str] = None
    """
    The url to download a trailer, should it exist.
    """
    background_url: Optional[str] = None
    """
    The url to download a background image, should it exist.
    """
    tags: List[str]
    """
    Tags associated with the video.   Noisy and long list.
    """

    def __init__(self):
        self.performers = []
        self.tags = []
        self.original_parsed_filename = FileNameParts()

    def as_dict(self):
        """
        Converts the info in to a dict that can be used
        by PartialFormatter to return a new path for a file.
        """
        if self.original_parsed_filename is None:
            self.original_parsed_filename = FileNameParts()
        return {
            "uuid": self.uuid,
            "date": self.date,
            "description": self.description,
            "name": self.name,
            "site": self.site.replace(" ", "") if self.site is not None else None,
            "full_site": self.site,
            "performers": " ".join(
                map(
                    lambda p: p.name,
                    filter(lambda p: p.role == "Female", self.performers),
                )
            )
            if self.performers is not None
            else None,
            "all_performers": " ".join(map(lambda p: p.name, self.performers))
            if self.performers is not None
            else None,
            "ext": self.original_parsed_filename.extension
            if self.original_parsed_filename is not None
            else None,
            "trans": self.original_parsed_filename.trans
            if self.original_parsed_filename is not None
            else None,
        }

    def new_file_name(self, template: str, infix: str = "(0)") -> str:
        """
        Constructs a new file name based on a template (describe in NamerConfig)
        """
        dictionary = self.as_dict()
        clean_dic = {k: str(sanitize_filename(str(v), platform=str(Platform.UNIVERSAL))) for k, v in dictionary.items()}
        fmt = PartialFormatter(missing="", bad_fmt="---")
        name = fmt.format(template, **clean_dic)
        if infix != str("(0)"):
            # will apply the infix before the file extension if just a file name, if a path, with apply
            # the infix after the fist part (first directory name) of the (sub)path
            path = PurePath(name)
            if len(path.parts) > 1:
                name = str(path.parent / (path.stem + infix + path.suffix))
            else:
                name = path.stem + infix + path.suffix
        return name


@dataclass(init=True, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class ComparisonResult:
    """
    Represents the comparison from a FileNameParts and a LookedUpFileInfo, it will be
    considered a match if the creation dates match, the studio matches, and the original
    scene/perform part of a file name can match any combination of the metadata about
    actor names and/or scene name.   RapidFuzz is used to make the comparison.
    """

    name: str
    name_match: float
    """
    How closely did the name found in FileNameParts match (via RapidFuzz string comparison)
    The performers and scene name found in LookedUpFileInfo.  Various combinations of performers
    and scene namer are used for attempted matching.
    """

    site_match: bool
    """
    Did the studios match between filenameparts and looked up
    """

    date_match: bool
    """
    Did the dates match between filenameparts and looked up
    """

    name_parts: FileNameParts
    """
    Parts of the file name that were parsed and used as search parameters.
    """

    looked_up: LookedUpFileInfo
    """
    Info pulled from the porndb.  When doing searches it will not include tags, only included when
    performing a lookup by id (which is done only after a match is made.)
    """

    def is_match(self) -> bool:
        """
        Returns true if site and creation data match exactly, and if the name fuzzes against
        the metadate to 90% or more (via RapidFuzz, and various concatenations of metadata about
        actors and scene name).
        """
        return self.site_match and self.date_match and self.name_match is not None and self.name_match >= 89.9


# noinspection PyDataclass
@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class Command:
    input_file: Path
    """
    This is the original user/machine input of a target path.
    If this path is a directory a movie is found within it (recursively).
    If this file is a the movie file itself, the parent directory is calculated.
    """
    target_movie_file: Path
    """
    The movie file this name is targeting.
    """
    target_directory: Optional[Path] = None
    """
    The containing directory of a File.  This may be the immediate parent directory, or higher up, depending
    on whether a directory was selected as the input to a naming process.
    """
    parsed_dir_name: bool
    """
    Was the input file a directory and is parsing directory names configured?
    """
    parsed_file: Optional[FileNameParts] = None
    """
    The parsed file name.
    """
    inplace: bool = False

    write_from_nfos: bool = False

    tpdb_id: Optional[str] = None

    config: NamerConfig


@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class ProcessingResults:
    """
    Returned from the namer.py process() function.   It contains information about if a match
    was found, and of so, where files were placed.  It also tracks if a directory was inputted
    to namer (rather than the exact movie file.)  That knowledge can be used to move directories
    and preserve relative files, or to delete left over artifacts.
    """

    search_results: Optional[List[ComparisonResult]] = None
    """
    True if a match was found in the porndb.
    """

    new_metadata: Optional[LookedUpFileInfo] = None
    """
    New metadata found for the file being processed.
    Sourced including queries against the porndb, which would be stored in search_results,
    or reading a .nfo xml file next to the video, with the file name identical except for
    the extension, which would be .nfo instead of .mp4,.mkv,.avi,.mov,.flv.
    """

    dir_file: Optional[Path] = None
    """
    Set if the input file for naming was a directory.   This has advantages, as clean up of other files is now possible,
    or all files can be moved to a destination specified in the field final_name_relative.
    """

    video_file: Optional[Path] = None
    """
    The location of the found video file.
    """

    parsed_file: Optional[FileNameParts] = None
    """
    The parsed file name.
    """

    final_name_relative: Optional[Path] = None
    """
    This is the full NamerConfig.new_relative_path_name string with all substitutions made.
    """
