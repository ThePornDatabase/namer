import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path, PurePath
from typing import Dict, List, Optional, Union

from pathvalidate import Platform, sanitize_filename

from namer.configuration import NamerConfig
from namer.fileinfo import FileInfo
from namer.name_formatter import PartialFormatter


@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class Performer:
    """
    Minimal info about a performer, name, and role.
    """

    name: str
    role: Optional[str]
    image: Optional[Union[Path, str]]
    """
    if available the performers gender, stored as a role.  example: "Female", "Male"
    Useful as many nzbs often don't include the scene name, but instead female performers names,
    or sometimes both.
    Other performers are also used in name matching, if females are attempted first.
    """

    def __init__(self, name, role=None, image=None):
        self.name = name
        self.role = role
        self.image = image

    def __str__(self):
        name = "Unknown" if self.name is None else self.name
        if self.role:
            return name + " (" + self.role + ")"

        return name

    def __repr__(self):
        return f"Performer[name={self.name}, role={self.role}, image={self.image}]"


class SceneType(str, Enum):
    SCENE = 'Scene'
    MOVIE = 'Movie'
    JAV = 'JAV'


class HashType(str, Enum):
    PHASH = 'PHASH'
    OSHASH = 'OSHASH'
    MD5 = 'MD5'


@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class SceneHash:
    hash: str
    type: HashType
    duration: Optional[int]

    def __init__(self, scene_hash: str, hash_type: HashType, duration: Optional[int] = None):
        self.hash = scene_hash
        self.type = hash_type
        self.duration = duration


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

    guid: Optional[str] = None
    """
    porndb guid/stashid
    """

    site: Optional[str] = None
    """
    Site where this video originated, DorcelClub/Deeper/etc.....
    """
    network: Optional[str] = None
    """
    Top level studio, like Vixen for Deeper.
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
    performers: List[Performer] = field(default_factory=list)
    """
    List of performers, containing names, and "roles" aka genders, for each performer.
    """
    # genres: List[str] = field(default_factory=list)
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
    original_parsed_filename: Optional[FileInfo] = None
    """
    The FileInfo used to build the original_query
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
    tags: List[str] = field(default_factory=list)
    """
    Tags associated with the video.   Noisy and long list.
    """
    hashes: List[SceneHash] = field(default_factory=list)
    """
    Hashes associated with the video.
    """
    type: Optional[SceneType] = None
    """
    movie or scene, a distinction without a difference.
    """
    duration: Optional[int] = None
    """
    Minute long run lenth of scene or movie.
    """
    resolution: Optional[int] = None
    """
    the width of video in pixels.
    """
    external_id: Optional[str] = None
    """
    Should the source site provide it, the id for the site.
    """
    is_collected: bool = False
    """
    Indicates if the current user has marked this video as part of their collection.
    """

    def __init__(self):
        self.performers = []
        self.tags = []
        self.hashes = []
        self.resolution = None
        self.original_parsed_filename = FileInfo()

    def as_dict(self, config: NamerConfig):
        """
        Converts the info in to a dict that can be used
        by PartialFormatter to return a new path for a file.
        """
        if not self.original_parsed_filename:
            self.original_parsed_filename = FileInfo()

        res = self.resolution
        res_str: Optional[str] = None
        if res:
            res_str = "2160p" if res == 2160 else f"{res}p" if res in [1080, 720, 480] else f"{res}"

        vr = ""
        if (self.site and self.site.lower() in config.vr_studios) or any(tag.strip().lower() in config.vr_tags for tag in self.tags):
            vr = "vr"

        if self.original_query and '/movies' in self.original_query and (self.site and self.site.lower().replace(" ", "") not in config.movie_data_preferred):
            self.type = SceneType.MOVIE
        elif self.original_query and '/jav' in self.original_query:
            self.type = SceneType.JAV
        else:
            self.type = SceneType.SCENE

        return {
            "uuid": self.uuid,
            "date": self.date,
            "year": self.date[0:4] if self.date else None,
            "description": self.description,
            "name": self.name,
            "site": self.site.replace(" ", "") if self.site else None,
            "full_site": self.site,
            "network": self.network.replace(" ", "") if self.network else None,
            "full_network": self.network,
            "performers": ", ".join(map(lambda p: p.name, filter(lambda p: p.role == "Female", self.performers))) if self.performers else None,
            "all_performers": ", ".join(map(lambda p: p.name, self.performers)) if self.performers else None,
            "ext": self.original_parsed_filename.extension if self.original_parsed_filename else None,
            "trans": self.original_parsed_filename.trans if self.original_parsed_filename else None,
            "vr": vr,
            "resolution": res_str,
            "type": self.type.value,
            "external_id": self.external_id,
        }

    def new_file_name(self, template: str, config: NamerConfig, infix: str = "(0)") -> str:
        """
        Constructs a new file name based on a template (describe in NamerConfig)
        """
        dictionary = self.as_dict(config)
        clean_dic = self.__cleanup_dictionary(dictionary)
        fmt = PartialFormatter(missing="", bad_fmt="---")
        name = fmt.format(template, **clean_dic)

        if infix != "(0)":
            # will apply the infix before the file extension if just a file name, if a path, with apply
            # the infix after the fist part (first directory name) of the (sub)path
            path = PurePath(name)
            name = path.stem + infix + path.suffix
            if path.parts:
                name = str(path.parent / name)

        if config.plex_hack:
            name = re.sub(r'[sS]\d{1,3}:?[eE]\d{1,3}', '', name)

        return name

    @staticmethod
    def __cleanup_dictionary(dictionary: Dict[str, Optional[str]]) -> Dict[str, str]:
        clean_dic = {}
        for key, value in dictionary.items():
            value = str(value) if value else ''

            if key != 'uuid':
                value = value.replace('/', ' ').replace('\\', ' ')

            value = sanitize_filename(value, platform=Platform.UNIVERSAL.value)
            clean_dic[key] = str(value)

        return clean_dic

    def found_via_phash(self) -> bool:
        return bool(self.original_query and '?hash=' in self.original_query)


@dataclass(init=True, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class ComparisonResult:
    """
    Represents the comparison from a FileInfo and a LookedUpFileInfo, it will be
    considered a match if the creation dates match, the studio matches, and the original
    scene/perform part of a file name can match any combination of the metadata about
    actor names and/or scene name.   RapidFuzz is used to make the comparison.
    """

    name: str
    name_match: float
    """
    How closely did the name found in FileInfo match (via RapidFuzz string comparison)
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

    name_parts: Optional[FileInfo]
    """
    Parts of the file name that were parsed and used as search parameters.
    """

    looked_up: LookedUpFileInfo
    """
    Info pulled from the porndb.  When doing searches it will not include tags, only included when
    performing a lookup by id (which is done only after a match is made.)
    """

    phash_distance: Optional[int]
    """
    How close searched hash to database one.
    """

    phash_duration: Optional[bool]
    """
    Duration diff with phash duration.
    """

    def is_phash_match(self, target_distance: int = 0) -> bool:
        """
        Returns true if match is a phash match.
        """
        return self.phash_distance is not None and self.phash_distance <= target_distance and self.phash_duration is not None

    def is_match(self, target: float = 94.9, target_distance: int = 0) -> bool:
        """
        Returns true if site and creation data match exactly, and if the name fuzzes against
        the metadate to 90% or more (via RapidFuzz, and various concatenations of metadata about
        actors and scene name) or is a phash match.
        """
        return bool(self.site_match and self.date_match and self.name_match and self.name_match >= target) or self.is_phash_match(target_distance)

    def is_super_match(self, target: float = 94.9, target_distance: int = 0) -> bool:
        """
        Returns true if site and creation data match exactly, and if the name fuzzes against
        the metadate to 95% or more (via RapidFuzz, and various concatenations of metadata about
        actors and scene name) and is a phash match.
        """
        return bool(self.site_match and self.date_match and self.name_match and self.name_match >= target) and self.is_phash_match(target_distance)


@dataclass(init=True, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class ComparisonResults:
    results: List[ComparisonResult]

    def get_match(self) -> Optional[ComparisonResult]:
        match = None
        if self.results and self.results[0].is_match():
            # verify the match isn't covering over a better namer match, if it is, no match shall be made
            # implying that the site and date on the name of the file may be wrong.   leave it for the user
            # to sort it out.
            match: Optional[ComparisonResult] = self.results[0]
            for potential in self.results[1:]:
                # Now that matches are unique in the list, don't match if there are multiple
                if match:
                    if not match.is_super_match() and potential.is_match() or potential.is_super_match():  # noqa: SIM114
                        match = None
                    elif not match.is_super_match() and not match.is_phash_match() and potential.name_match > match.name_match:
                        match = None
        return match
