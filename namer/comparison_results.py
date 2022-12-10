from dataclasses import dataclass, field
from pathlib import PurePath
from typing import List, Optional

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
    image: Optional[str]
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
    type: Optional[str] = None
    """
    movie or scene, a distinction without a difference.
    """
    duration: Optional[float] = None
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

    def __init__(self):
        self.performers = []
        self.tags = []
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
            res_str = "4k" if res == 2160 else f"{res}p" if res in [1080, 720, 480] else f"{res}"

        vr = ""
        if (self.site and self.site.lower() in config.vr_studios) or any(tag.strip().lower() in config.vr_tags for tag in self.tags):
            vr = "vr"

        if self.original_query and '/movies' in self.original_query and (self.site and self.site.lower().replace(" ", "") not in config.movie_data_preferred):
            self.type = 'movie'
        else:
            self.type = 'scene'

        return {
            "uuid": self.uuid,
            "date": self.date,
            "description": self.description,
            "name": self.name,
            "site": self.site.replace(" ", "") if self.site else None,
            "full_site": self.site,
            "performers": " ".join(map(lambda p: p.name, filter(lambda p: p.role == "Female", self.performers))) if self.performers else None,
            "all_performers": " ".join(map(lambda p: p.name, self.performers)) if self.performers else None,
            "ext": self.original_parsed_filename.extension if self.original_parsed_filename else None,
            "trans": self.original_parsed_filename.trans if self.original_parsed_filename else None,
            "vr": vr,
            "resolution": res_str,
            "type": self.type,
            "external_id": self.external_id,
        }

    def new_file_name(self, template: str, config: NamerConfig, infix: str = "(0)") -> str:
        """
        Constructs a new file name based on a template (describe in NamerConfig)
        """
        dictionary = self.as_dict(config)
        clean_dic = {k: str(sanitize_filename(str(v), platform=str(Platform.UNIVERSAL))) for k, v in dictionary.items()}
        fmt = PartialFormatter(missing="", bad_fmt="---")
        name = fmt.format(template, **clean_dic)

        if infix != "(0)":
            # will apply the infix before the file extension if just a file name, if a path, with apply
            # the infix after the fist part (first directory name) of the (sub)path
            path = PurePath(name)
            name = path.stem + infix + path.suffix
            if path.parts:
                name = str(path.parent / name)

        return name

    def found_via_phash(self) -> bool:
        return True if self.source_url and "/hash/" in self.source_url else False


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

    name_parts: FileInfo
    """
    Parts of the file name that were parsed and used as search parameters.
    """

    looked_up: LookedUpFileInfo
    """
    Info pulled from the porndb.  When doing searches it will not include tags, only included when
    performing a lookup by id (which is done only after a match is made.)
    """

    phash_match: bool
    """
    Was this matched found via a phash, and not the name.
    """

    def is_match(self) -> bool:
        """
        Returns true if site and creation data match exactly, and if the name fuzzes against
        the metadate to 90% or more (via RapidFuzz, and various concatenations of metadata about
        actors and scene name).
        """
        return bool(self.site_match and self.date_match and self.name_match and self.name_match >= 94.9) or self.phash_match


@dataclass(init=True, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class ComparisonResults:
    results: List[ComparisonResult]

    def get_match(self) -> Optional[ComparisonResult]:
        match = None
        if self.results and len(self.results) > 0 and self.results[0].is_match():
            # verify the match isn't covering over a better namer match, if it is, no match shall be made
            # implying that the site and date on the name of the file may be wrong.   leave it for the user
            # to sort it out.
            match: Optional[ComparisonResult] = self.results[0]
            for potential in self.results[1:]:
                if match and match.name_match < potential.name_match:
                    match = None
        return match
