from dataclasses import dataclass
from pathlib import PurePath
from typing import List, Optional

from namer.filenameparts import FileNameParts
from namer.name_formatter import PartialFormatter
from pathvalidate import Platform, sanitize_filename


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
        if not self.original_parsed_filename:
            self.original_parsed_filename = FileNameParts()

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
            if path.parts:
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
        return bool(self.site_match and self.date_match and self.name_match and self.name_match >= 89.9)


@dataclass(init=True, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class ComparisonResults:
    results: List[ComparisonResult]
