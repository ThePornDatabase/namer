"""
Types shared by all the files in this project, used as interfaces for moving data.
"""

from configparser import ConfigParser
from dataclasses import dataclass
from typing import List
import os
import configparser
import re
import sys
import string
from pathlib import Path, PurePath
import logging
import random
from pathvalidate import Platform, sanitize_filename

logger = logging.getLogger('types')

def _verify_dir(name: str, file_name: Path) -> bool:
    """
    verify a config directory exist. return false if verification fails
    """
    if file_name is not None and not file_name.is_dir():
        logger.error("Configured directory %s: %s is not a directory or not accessible", name, file_name)
        return False
    return True

def _verify_name_string(name: str, name_string: str) -> bool:
    """
    Verify the name format string.
    """
    info = LookedUpFileInfo()
    try:
        formatter = PartialFormatter()
        formatter.format(name_string, **info.asdict())
        return True
    except KeyError as key_error:
        logger.error("Configuration %s is not a valid file name format, please check %s", name, name_string)
        logger.error("Error message: %s", key_error)
        return False

class PartialFormatter(string.Formatter):
    """
    Used for formating NamerConfig.inplace_name and NamerConfig.
    """

    supported_keys = ['date','description','name','site','full_site','performers','all_performers','act','ext','trans']

    def __init__(self, missing='~~', bad_fmt='!!'):
        self.missing, self.bad_fmt=missing, bad_fmt

    def get_field(self, field_name, args, kwargs):
        # Handle a key not found
        try:
            val=super().get_field(field_name, args, kwargs)
        except (KeyError, AttributeError) as err:
            val=None,field_name
            if not field_name in self.supported_keys:
                raise KeyError(f"Key {field_name} not in support keys: {self.supported_keys}") from err
        return val

    def format_field(self, value, format_spec):
        if value is None:
            return self.missing
        try:
            if re.match(r'.\d+s', format_spec):
                value = value + format_spec[0] * int(format_spec[1:-1])
                format_spec = ''
            if re.match(r'.\d+p', format_spec):
                value = format_spec[0] * int(format_spec[1:-1]) + value
                format_spec = ''
            if re.match(r'.\d+i', format_spec):
                value = format_spec[0] * int(format_spec[1:-1]) + value + format_spec[0] * int(format_spec[1:-1])
                format_spec = ''
            return super().format_field(value, format_spec)
        except ValueError:
            if self.bad_fmt is not None:
                return self.bad_fmt
            raise

@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class NamerConfig():
    """
    Configuration for namer and namer_watchdog
    """

    # pylint: disable=too-many-instance-attributes

    porndb_token: str = None
    """
    token to access porndb.
    sign up here: https://metadataapi.net/
    """

    inplace_name: str = '{site} - {date} - {name}.{ext}'
    """
    How to write output file name.  When namer.py is run this is applied in place
    (next to the file to be processed).
    When run from namer_watchdog.py this will be written in to the successdir.

    Supports stand python 3 formating, as well as:
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

    min_file_size = 300
    """
    minimum file size to process in MB, ignored if a file is to be processed
    """

    prefer_dir_name_if_available = True
    """
    If a directory name is to be prefered over a file name.
    """

    set_uid = None
    """
    UID Settings for new/moved files/dirs.
    """

    set_gid = None
    """
    GID Settings for new/moved files/dirs.
    """

    write_namer_log = False
    """
    Should a log of comparisons be written next to processed video files.
    """

    set_dir_permissions = 775
    """
    Permissions Settings for new/moved dirs.
    """

    set_file_permissions = 664
    """
    Permissions Settings for new/moved file.
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
    Should genres pulled from the porndb be added to the file?   These genres are noisey and
    not recommend for use.  If this is false a single default genere will be used.
    """

    default_genre: str = "Adult"
    """
    If genre's are not copied this is the default genere added to files.
    Default value is adult.
    """

    language: str = None
    """
    if language is set it will be used to select the default audio stream in an mp4 that has too many default stream
    to play correct in quicktime/apple tv.   If the language isn't found or is already the only default no action is
    taken, no streams (audio/video) are re-encoded.  Available here: https://iso639-3.sil.org/code_tables/639/data/
    """

    new_relative_path_name: str = '{site} - {date} - {name}/{site} - {date} - {name}.{ext}'
    """
    like inplace_name above used for local call for renaming, this instead is used to move a file/dir to a location relative
    to the dest_dir below on successful matching/tagging.
    """

    del_other_files = False
    """
    when processing a directory in the dest dir, should extra files besides the largest video be removed?
    or attempt to move them to a subdirectory specified in new_relative_path_name, if one exist.
    """

    watch_dir: Path = None
    """
    If running in watchdog mode, director where new downloads go.
    """

    work_dir: Path = None
    """
    If running in watchdog mode, temporary directory where work is done.
    a log file shows attempted matchs and match closeness.
    """

    failed_dir: Path = None
    """
    If running in watchdog mode, Should processing fail the file or directory is moved here.
    Files can be manually moved to watchdir to force reprocessing.
    """

    dest_dir: Path = None
    """
    If running in watchdog mode, dir where finalized files get written.
    """

    retry_time: str = None
    """
    Time to retry failed items every day.
    """

    def __init__(self):
        if sys.platform != "win32":
            self.set_uid = os.getuid()
            self.set_gid = os.getgid()


    def __str__(self):
        token = "None In Set, Go to https://metadatapi.net/ to get one!"
        if self.porndb_token is not None:
            token = re.sub(r'.', '*', self.porndb_token)
        output = 'Namer Config:\n'
        output += f'porndb_token: {token}\n'
        output += f"  inplace_name: {self.inplace_name}\n"
        output += f"  prefer_dir_name_if_available: {self.prefer_dir_name_if_available}\n"
        output += f"  set_uid: {self.set_uid}\n"
        output += f"  set_gid: {self.set_gid}\n"
        output += f"  write_namer_log: {self.write_namer_log}\n"
        output += f"  set_dir_permissions: {self.set_dir_permissions}\n"
        output += f"  set_file_permissions: {self.set_file_permissions}\n"
        output += "Tagging Config:\n"
        output += f"  enabled_tagging: {self.enabled_tagging}\n"
        output += f"  enabled_poster: {self.enabled_poster}\n"
        output += f"  enable_metadataapi_genres: {self.enable_metadataapi_genres}\n"
        output += f"  default_genre: {self.default_genre}\n"
        output += f"  language: {self.language}\n"
        output += "Watchdog Config:\n"
        output += f"  min_file_size: {self.min_file_size}mb\n"
        output += f"  del_other_files: {self.del_other_files}\n"
        output += f"  new_relative_path_name: {self.new_relative_path_name}\n"
        output += f"  watch_dir: {self.watch_dir}\n"
        output += f"  work_dir: {self.work_dir}\n"
        output += f"  failed_dir: {self.failed_dir}\n"
        output += f"  dest_dir: {self.dest_dir}\n"
        output += f"  retry_time: {self.retry_time}\n"
        return output


    def verify_config(self) -> bool:
        """
        Verifies the contents of your config file. Returns False if configuration failed.
        """
        success = True
        if self.enable_metadataapi_genres is not True and self.default_genre is None:
            logger.error("Sinse enable_metadataapi_genres is not True, you must specify a default_genre")
            success = False
        success = _verify_dir("watch_dir", self.watch_dir) and success
        success = _verify_dir("work_dir", self.work_dir) and success
        success = _verify_dir("failed_dir", self.failed_dir) and success
        success = _verify_dir("dest_dir", self.dest_dir) and success
        success = _verify_name_string("inplace_name", self.inplace_name) and success
        success = _verify_name_string("new_relative_path_name", self.new_relative_path_name) and success
        return success


def from_config(config : ConfigParser) -> NamerConfig:
    """
    Given a config parser pointed at a namer.cfg file, return a NamerConfig with the file's parameters.
    """
    namer_config = NamerConfig()
    namer_config.porndb_token = config.get('namer','porndb_token', fallback=None)
    namer_config.inplace_name = config.get('namer','inplace_name',fallback='{site} - {date} - {name}.{ext}')
    namer_config.prefer_dir_name_if_available = config.getboolean('namer','prefer_dir_name_if_available',fallback=False)
    namer_config.min_file_size = config.getint('namer','min_file_size',fallback=100)
    namer_config.set_uid = config.getint('namer','set_uid',fallback=None)
    namer_config.set_gid = config.getint('namer','set_gid',fallback=None)
    namer_config.write_namer_log = config.getboolean('namer','write_namer_log',fallback=False)
    namer_config.set_dir_permissions = config.get('namer','set_dir_permissions',fallback=775)
    namer_config.set_file_permissions = config.get('namer','set_file_permissions',fallback=664)
    namer_config.enabled_tagging = config.getboolean('metadata','enabled_tagging',fallback=True)
    namer_config.enabled_poster = config.getboolean('metadata','enabled_poster',fallback=True)
    namer_config.enable_metadataapi_genres = config.getboolean('metadata','enable_metadataapi_genres',fallback=False)
    namer_config.default_genre = config.get('metadata','default_genre',fallback='Adult')
    namer_config.language = config.get('metadata','language',fallback=None)
    namer_config.new_relative_path_name = config.get('watchdog','new_relative_path_name',
        fallback='{site} - {date} - {name}/{site} - {date} - {name}.{ext}')
    namer_config.del_other_files = config.getboolean('watchdog','del_other_files',fallback=False)
    watch_dir = config.get('watchdog','watch_dir',fallback=None)
    if watch_dir is not None:
        namer_config.watch_dir = Path(watch_dir)
    work_dir = config.get('watchdog','work_dir',fallback=None)
    if work_dir is not None:
        namer_config.work_dir = Path(work_dir)
    failed_dir = config.get('watchdog','failed_dir',fallback=None)
    if failed_dir is not None:
        namer_config.failed_dir = Path(failed_dir)
    dest_dir = config.get('watchdog','dest_dir',fallback=None)
    if dest_dir is not None:
        namer_config.dest_dir = Path(dest_dir)

    namer_config.retry_time = config.get('watchdog','retry_time',fallback=None)
    if namer_config.retry_time is None:
        namer_config.retry_time = "03:"+random.choice(["01", "11" ,"21", "31", "41", "51"])
    return namer_config


def default_config() -> NamerConfig:
    """
    Attempts reading various locations to fine a namer.cfg file.
    """
    found_config = None
    if os.environ.get('NAMER_CONFIG'):
        namer_cfg = os.environ.get('NAMER_CONFIG')
        if Path(namer_cfg).is_file():
            logger.info("Using config file from NAMER_CONFIG environment %s",namer_cfg)
            found_config = namer_cfg
    if found_config is None:
        namer_cfg = Path('./namer.cfg')
        if namer_cfg.is_file():
            logger.info("Using local executable config: %s",namer_cfg.absolute())
            found_config = namer_cfg
    if found_config is None:
        namer_cfg = Path.home() / ".namer.cfg"
        if namer_cfg.is_file():
            logger.info("Using homer dir config: %s",namer_cfg)
            found_config = namer_cfg
    if found_config is None:
        namer_cfg = Path(__file__).absolute().parent / 'namer.cfg'
        if namer_cfg.is_file():
            logger.info("Using local executable config: %s",namer_cfg)
            found_config = namer_cfg


    config = configparser.ConfigParser()
    config.read(namer_cfg)
    return from_config(config)

@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class FileNameParts:
    """
    Represents info parsed from a file name, usually of an nzb, named something like:
    'EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.2160p.MP4-GAYME-xpost'
    or
    'DorcelClub.20.12..Aya.Benetti.Megane.Lopez.And.Bella.Tina.2160p.MP4-GAYME-xpost'
    """

    # pylint: disable=too-many-instance-attributes

    site: str = ""
    """
    Site the file originated from, "DorcelClub", "EvilAngel", etc.
    """
    date: str = ""
    """
    formated: YYYY-mm-dd
    """
    trans: bool = False
    """
    If the name originally started with an "TS" or "ts"
    it will be stripped out and placed in a seperate location, aids in matching, useable to genre mark content.
    """
    name: str = ""
    act: str = None
    """
    If the name originally ended with an "act ###" or "part ###"
    it will be stripped out and placed in a seperate location, aids in matching.
    """
    extension: str = ""
    """
    The file's extension (always .mp4)
    """
    resolution: str = ""
    """
    Resolution, if the file name makes a claim about resolution. (480p, 720p, 1080p, 4k)
    """
    source_file_name: str = ""
    """
    What was originally parsed.
    """

    def __str__(self) -> str:
        return f"""site: {self.site}
        date: {self.date}
        trans: {self.trans}
        name: {self.name}
        act: {self.act}
        extension: {self.extension}
        original full name: {self.source_file_name}
        """

@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class Performer:
    """
    Minimal info about a perform, name, and role.
    """
    name: str
    role: str
    """
    if available the performers gender, stored as a role.  example: "Female", "Male"
    Useful as many nzbs often don't include the scene name, but instead female performers names,
    or sometimes both.
    Other performers are also used in name matching, if females are attempted first.
    """

    def __init__(self, name=None, role=None):
        self.name = name
        self.role = role

    def __str__(self):
        if self.role is not None:
            return self.name + " (" + self.role + ")"
        return self.name

    def __repr__(self):
        return f'Performer[name={self.name}, role={self.role}]'


@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class LookedUpFileInfo():
    """
    Information from a call to the porndb about a specific scene.
    """

    # pylint: disable=too-many-instance-attributes

    uuid: str = ""
    """
    porndb scene id, allowing lookup of more metadata, (tags)
    """

    site: str = ""
    """
    Site where this video originated, DorcelClub/Deeper/etc.....
    """
    date: str = ""
    """
    date of initial release, formated YYYY-mm-dd
    """
    name: str = ""
    """
    Name of the scene in this video
    """
    description: str = ""
    """
    Description of the action in this video
    """
    source_url: str = ""
    """
    Original source location of this video
    """
    poster_url: str = ""
    """
    Url to download a poster for this video
    """
    performers: List[Performer]
    """
    List of performers, containing names, and "roles" aka genders, for each performer.
    """
    genres: List[str]
    """
    List of genres, per porndb.  Tends to be noisey.
    """
    origninal_response: str = ""
    """
    json reponse parsed in to this object.
    """
    original_query: str = ""
    """
    url query used to get the above json response
    """
    original_parsed_filename: FileNameParts
    """
    The FileNameParts used to build the orignal_query
    """
    look_up_site_id: str = ""
    """
    ID Used by the queried site to identify the video
    """

    tags: List[str]
    """
    Tags associated with the video.   Noisy and long list.
    """

    def __init__(self):
        self.performers = []
        self.tags = []
        self.original_parsed_filename = FileNameParts()

    def asdict(self):
        """
        Converts the info in to a dict that can be used
        by PartialFormatter to return a new path for a file.
        """
        if self.original_parsed_filename is None:
            self.original_parsed_filename = FileNameParts()
        return {'uuid': self.uuid,
                'date': self.date,
                'description': self.description,
                'name': self.name,
                'site': self.site.replace(' ',''),
                'full_site': self.site,
                'performers': " ".join(map(lambda p: p.name, filter( lambda p: p.role == 'Female' , self.performers))),
                'all_performers': " ".join(map( lambda p: p.name , self.performers)),
                'act': self.original_parsed_filename.act,
                'ext': self.original_parsed_filename.extension,
                'trans': self.original_parsed_filename.trans}

    def new_file_name(self, template: str, infix: str = "(0)") -> str:
        """
        Constructs a new file name based on a template (describe in NamerConfig)
        """
        dictionary = self.asdict()
        clean_dic = { k: str(sanitize_filename(str(v), platform=Platform.UNIVERSAL))  for k, v in dictionary.items() }
        fmt = PartialFormatter(missing="", bad_fmt="---")
        name = fmt.format(template, **clean_dic)
        if infix != str("(0)"):
            # will apply the infix before the file extension if just a file name, if a path, with apply
            #the infix after the fist part (first directory name) of the (sub)path
            path = PurePath(name)
            if len(path.parts) > 1:
                name = str(path.parent / ( path.stem + infix + path.suffix ))
            else:
                name = path.stem + infix + path.suffix
        return name

@dataclass(init=True, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class ComparisonResult:
    """
    Represents the comparison from a FileNameParts and a LookedUpFileInfo, it will be
    consider a match if the creation dates match, the studio matches, and the original
    scene/perform part of a the file name can match any combination of the metadata about
    actor names and/or scene name.   RapidFuzz is used to make the comparison.
    """

    name: str
    name_match: float
    """
    How closely did the name found in FileNameParts match (via RapidFuzz string comparison)
    The performers and scene name found in LookedUpFileInfo.  Various combinations of performers
    and scene namer are used for attempted matching.
    """

    sitematch: bool
    """
    Did the studios match between filenameparts and lookedup
    """


    datematch: bool
    """
    Did the dates match between filenameparts and lookedup
    """

    name_parts: FileNameParts
    """
    Parts of the file name that were parsed and used as search parameters.
    """

    looked_up: LookedUpFileInfo
    """
    Info pulled from the porndb.  When doing searchs it will not include tags, only included when
    performing a lookup by id (which is done only after a match is made.)
    """

    def is_match(self) -> bool:
        """
        Returns true if site and creation data match exactly, and if the name fuzzes against
        the metadate to 90% or more (via RapidFuzz, and various concatinations of metadata about
        actors and scene name).
        """
        return self.sitematch and self.datematch and self.name_match >= 89.9



@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class ProcessingResults:
    """
    Returned from the namer.py's process() function.   It contains information about if a match
    was found, and of so, where files were placed.  It also tracks if a directory was inputed
    to namer (rather than the exact movie file.)  That knowledge can be used to move directories
    and preserve relative files, or to delete left over artifacts.
    """

    search_results: List[ComparisonResult] = None
    """
    True if a match was found in the porndb.
    """

    new_metadata: LookedUpFileInfo = None
    """
    New metadata found for the file being processed.
    Sourced including queries against the porndb, which would be stored in search_results,
    or reading a .nfo xml file next to the video, with the file name identical exept for
    the extension, which would be .nfo instead of .mkv, or .mp4.
    """

    dirfile: Path = None
    """
    Set if the input file for naming was a directory.   This has advantages, as clean up of other files is now possible,
    or all files can be moved to a destination specified in the field final_name_relative.
    """

    video_file: Path = None
    """
    The location of the found video file.
    """

    parsed_file: FileNameParts = None
    """
    The parsed file name.
    """

    final_name_relative: str = None
    """
    This is the full NamerConfig.new_relative_path_name string with all substitutions made.
    """

    namer_log_file: Path = None
    """
    If a log file was written, where it was stored.
    """
