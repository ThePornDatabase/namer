from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import List, Optional

from namer.configuration import NamerConfig
from namer.name_formatter import PartialFormatter
from pathvalidate import Platform, sanitize_filename


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
