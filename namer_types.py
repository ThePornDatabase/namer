from configparser import ConfigParser
from dataclasses import dataclass
from typing import List
import os
import configparser
import re
import sys
import string
from pathlib import Path
import logging

logger = logging.getLogger('types')

class PartialFormatter(string.Formatter):

    supported_keys = ['date','description','name','site','performers','all_performers','act','ext','trans']

    def __init__(self, missing='~~', bad_fmt='!!'):
        self.missing, self.bad_fmt=missing, bad_fmt

    def get_field(self, field_name, args, kwargs):
        # Handle a key not found
        try:
            val=super(PartialFormatter, self).get_field(field_name, args, kwargs)
            # Python 3, 'super().get_field(field_name, args, kwargs)' works
        except (KeyError, AttributeError):
            val=None,field_name 
            if not field_name in self.supported_keys:
                raise KeyError("Key {} not in support keys: {}".format(field_name, self.supported_keys))
        return val 

    def format_field(self, value, spec):
        # handle an invalid format
        if value==None: return self.missing
        try:
            if re.match(r'.\d+s', spec):
                value = value + spec[0] * int(spec[1:-1])
                spec = ''
            if re.match(r'.\d+p', spec):
                value = spec[0] * int(spec[1:-1]) + value
                spec = ''
            if re.match(r'.\d+i', spec):
                value = spec[0] * int(spec[1:-1]) + value + spec[0] * int(spec[1:-1]) 
                spec = ''      
            return super(PartialFormatter, self).format_field(value, spec)
        except ValueError:
            if self.bad_fmt is not None: return self.bad_fmt   
            else: raise

@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class NamerConfig():

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
    * 'site' - the site name, Brazzers, Deeper, etc
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

    watch_dir: str = None
    """
    If running in watchdog mode, director where new downloads go.
    """

    work_dir: str = None
    """
    If running in watchdog mode, temporary directory where work is done.
    a log file shows attempted matchs and match closeness.
    """

    failed_dir: str = None
    """
    If running in watchdog mode, Should processing fail the file or directory is moved here.
    Files can be manually moved to watchdir to force reprocessing.
    """

    dest_dir: str = None
    """
    If running in watchdog mode, dir where finalized files get written.
    """

    def __init__(self):
        if sys.platform != "win32":
            self.set_uid = os.getuid()
            self.set_gid = os.getgid()


    def __str__(self):
        str = "Namer Config:\n"
        if self.porndb_token != None:
            str += "  porndb_token: {}\n".format(re.sub(r'.', '*', self.porndb_token))
        else:
            str += "  porndb_token: None In Set, Go to https://metadatapi.net/ to get one!\n"   

        str += "  inplace_name: {}\n".format(self.inplace_name)
        str += "  prefer_dir_name_if_available: {}\n".format(self.prefer_dir_name_if_available)
        str += "  set_uid: {}\n".format(self.set_uid)
        str += "  set_gid: {}\n".format(self.set_gid)
        str += "  set_dir_permissions: {}\n".format(self.set_dir_permissions)
        str += "  set_file_permissions: {}\n".format(self.set_file_permissions)
        str += "Tagging Config:\n"
        str += "  enabled_tagging: {}\n".format(self.enabled_tagging)
        str += "  enabled_poster: {}\n".format(self.enabled_poster)
        str += "  enable_metadataapi_genres: {}\n".format(self.enable_metadataapi_genres)
        str += "  default_genre: {}\n".format(self.default_genre)
        str += "  language: {}\n".format(self.language)
        str += "Watchdog Config:\n"
        str += "  min_file_size: {}mb\n".format(self.min_file_size)
        str += "  del_other_files: {}\n".format(self.del_other_files)
        str += "  new_relative_path_name: {}\n".format(self.new_relative_path_name)
        str += "  watch_dir: {}\n".format(self.watch_dir)
        str += "  work_dir: {}\n".format(self.work_dir)
        str += "  failed_dir: {}\n".format(self.failed_dir)
        str += "  dest_dir: {}\n".format(self.dest_dir)
        return str


def fromConfig(config : ConfigParser) -> NamerConfig:
    namerConfig = NamerConfig()
    namerConfig.porndb_token = config.get('namer','porndb_token', fallback=None)
    namerConfig.inplace_name = config.get('namer','output',fallback='{site} - {date} - {name}.{ext}')
    namerConfig.prefer_dir_name_if_available = config.getboolean('namer','prefer_dir_name_if_available',fallback=False)
    namerConfig.min_file_size = config.getint('namer','min_file_size',fallback=100)
    namerConfig.set_uid = config.getint('namer','set_uid',fallback=None)
    namerConfig.set_gid = config.getint('namer','set_gid',fallback=None)
    namerConfig.set_dir_permissions = config.get('namer','set_dir_permissions',fallback=775)
    namerConfig.set_file_permissions = config.get('namer','set_file_permissions',fallback=664)
    namerConfig.enabled_tagging = config.getboolean('metadata','enabled_tagging',fallback=True)
    namerConfig.enabled_poster = config.getboolean('metadata','enabled_poster',fallback=True)
    namerConfig.enable_metadataapi_genres = config.getboolean('metadata','enable_metadataapi_genres',fallback=False)
    namerConfig.default_genre = config.get('metadata','default_genre',fallback='Adult')
    namerConfig.language = config.get('metadata','language',fallback=None)
    namerConfig.new_relative_path_name = config.get('metadata','new_relative_path_name',fallback='{site} - {date} - {name}/{site} - {date} - {name}.{ext}')
    namerConfig.del_other_files = config.getboolean('watchdog','del_other_files',fallback=False)
    namerConfig.watch_dir = config.get('watchdog','watch_dir',fallback=None)
    namerConfig.work_dir = config.get('watchdog','work_dir',fallback=None)
    namerConfig.failed_dir = config.get('watchdog','failed_dir',fallback=None)
    namerConfig.dest_dir = config.get('watchdog','dest_dir',fallback=None)
    return namerConfig


def defaultConfig() -> NamerConfig:
    found_config = None
    if os.environ.get('NAMER_CONFIG'):
        namer_cfg = os.environ.get('NAMER_CONFIG')
        if (os.path.isfile(namer_cfg)):
            logger.info("Using config file from NAMER_CONFIG environment {}".format(namer_cfg))
            found_config = namer_cfg
    if found_config == None:
        namer_cfg = './namer.cfg'
        if os.path.isfile(namer_cfg):
            logger.info("Using local executable config: {}".format(namer_cfg))
            found_config = namer_cfg
    if found_config == None:
        namer_cfg = os.path.join(Path.home(), ".namer.cfg")
        if os.path.isfile(namer_cfg):
            logger.info("Using homer dir config: {}".format(namer_cfg))
            found_config = namer_cfg
    if found_config == None:
        namer_cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)),'namer.cfg')
        if os.path.isfile(namer_cfg):
            logger.info("Using local executable config: {}".format(namer_cfg))
            found_config = namer_cfg        


    config = configparser.ConfigParser()
    config.read(namer_cfg)
    return fromConfig(config)

@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class FileNameParts:
    """
    Represents info parsed from a file name, usually of an nzb, named something like:
    'EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.2160p.MP4-GAYME-xpost'
    or
    'DorcelClub.20.12..Aya.Benetti.Megane.Lopez.And.Bella.Tina.2160p.MP4-GAYME-xpost'
    """
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
    act: str = ""
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
       return "site: {}\ndate: {}\ntrans: {}\nname: {}\nact: {}\nextension: {}\noriginal full name: {}\n".format( 
       self.site,
       self.date,
       self.trans,
       self.name,
       self.act,
       self.extension,
       self.source_file_name)

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
        if self.role != None:
            return self.name + " (" + self.role + ")" 
        else:
            return self.name 

    def __repr__(self):
        return 'Performer[name=' + self.name + ', role=%s' % self.role +']'


@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class LookedUpFileInfo():
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
    
    def asdict(self):
        return {'uuid': self.uuid,
                'date': self.date,
                'description': self.description,
                'name': self.name,
                'site': self.site,
                'performers': " ".join(map(lambda p: p.name, filter( lambda p: p.role == 'Female' , self.performers))),
                'all_performers': " ".join(map( lambda p: p.name , self.performers)),
                'act': self.original_parsed_filename.act,
                'ext': self.original_parsed_filename.extension,
                'trans': self.original_parsed_filename.trans}

    def new_file_name(self, template: str):
        dict = self.asdict()
        fmt = PartialFormatter(missing="", bad_fmt="---")
        name = fmt.format(template, **dict)
        return name

@dataclass(init=True, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class ComparisonResult:
    name: str
    name_match: float
    sitematch: bool
    datematch: bool
    name_parts: FileNameParts
    looked_up: LookedUpFileInfo

    def is_match(self) -> bool:
        return self.sitematch and self.datematch and self.name_match >= 89.9



@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class ProcessingResults:
    found: bool = False
    dirfile: str = None
    video_file: str = None
    namer_log_file: str = None
    final_name_relative: str = None
