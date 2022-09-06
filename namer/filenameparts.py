"""
Parse string in to FileNamePart define in namer_types.
"""
from dataclasses import dataclass
import re
from pathlib import PurePath
from typing import Optional, Pattern

from loguru import logger

from namer.database import abbreviations


DEFAULT_REGEX_TOKENS = "{_site}{_sep}{_optional_date}{_ts}{_name}{_dot}{_ext}"


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


def name_cleaner(name: str) -> str:
    """
    Given the name parts, following a date, but preceding the file extension, attempt to glean
    extra information and discard useless information for matching with the porndb.
    """
    # truncating cruft
    for size in ["2160p", "1080p", "720p", "4k", "3840p"]:
        name = re.sub(r"[.\- ]" + size + r"[.\- ]?.*", "", name)
    # remove trailing ".XXX."
    name = re.sub(r"[.\- ]?XXX[.\- ]?.*$", "", name)
    name = re.sub(r"\.", " ", name)
    return name


def parser_config_to_regex(tokens: str) -> Pattern[str]:
    """
    ``{_site}{_sep}{_optional_date}{_ts}{_name}{_dot}{_ext}``

    ``Site - YYYY.MM.DD - TS - name.mkv``

    ```
    _sep            r'[\\.\\- ]+'
    _site           r'(?P<site>[a-zA-Z0-9\\'\\.\\-\\ ]*?[a-zA-Z0-9]*?)'
    _date           r'(?P<year>[0-9]{2}(?:[0-9]{2})?)[\\.\\- ]+(?P<month>[0-9]{2})[\\.\\- ]+(?P<day>[0-9]{2})'
    _optional_date  r'(?:(?P<year>[0-9]{2}(?:[0-9]{2})?)[\\.\\- ]+(?P<month>[0-9]{2})[\\.\\- ]+(?P<day>[0-9]{2})[\\.\\- ]+)?'
    _ts             r'((?P<trans>[T|t][S|s])'+_sep+'){0,1}'
    _name           r'(?P<name>(?:.(?![0-9]{2,4}[\\.\\- ][0-9]{2}[\\.\\- ][0-9]{2}))*)'
    _dot            r'\\.'
    _ext            r'(?P<ext>[a-zA-Z0-9]{3,4})$'
    ```
    """

    _sep = r"[\.\- ]+"
    _site = r"(?P<site>.*?)"
    _date = r"(?P<year>[0-9]{2}(?:[0-9]{2})?)[\.\- ]+(?P<month>[0-9]{2})[\.\- ]+(?P<day>[0-9]{2})"
    _optional_date = r"(?:(?P<year>[0-9]{2}(?:[0-9]{2})?)[\.\- ]+(?P<month>[0-9]{2})[\.\- ]+(?P<day>[0-9]{2})[\.\- ]+)?"
    _ts = r"((?P<trans>[T|t][S|s])" + _sep + "){0,1}"
    _name = r"(?P<name>(?:.(?![0-9]{2,4}[\.\- ][0-9]{2}[\.\- ][0-9]{2}))*)"
    _dot = r"\."
    _ext = r"(?P<ext>[a-zA-Z0-9]{3,4})$"
    regex = tokens.format_map(
        {
            "_site": _site,
            "_date": _date,
            "_optional_date": _optional_date,
            "_ts": _ts,
            "_name": _name,
            "_ext": _ext,
            "_sep": _sep,
            "_dot": _dot,
        }
    )
    return re.compile(regex)


def parse_file_name(filename: str, regex_config: str = DEFAULT_REGEX_TOKENS) -> FileNameParts:
    """
    Given an input name of the form site-yy.mm.dd-some.name.part.1.XXX.2160p.mp4,
    parses out the relevant information in to a structure form.
    """
    filename = replace_abbreviations(filename)
    regex = parser_config_to_regex(regex_config)
    file_name_parts = FileNameParts()
    file_name_parts.extension = PurePath(filename).suffix[1:]
    match = regex.search(filename)
    if match:
        if match.groupdict().get("year"):
            prefix = "20" if len(match.group("year")) == 2 else ""
            file_name_parts.date = prefix + match.group("year") + "-" + match.group("month") + "-" + match.group("day")

        if match.groupdict().get("name"):
            file_name_parts.name = name_cleaner(match.group("name"))

        if match.groupdict().get("site"):
            file_name_parts.site = match.group("site")

        if match.groupdict().get("trans"):
            trans = match.group("trans")
            file_name_parts.trans = bool(trans and trans.strip().upper() == "TS")

        file_name_parts.extension = match.group("ext")
        file_name_parts.source_file_name = filename
    else:
        logger.warning("Could not parse target name which may be a file (or directory) name depending on settings and input: {}", filename)

    return file_name_parts


def replace_abbreviations(text: str):
    for abbreviation, full in abbreviations.items():
        r = re.compile(fr'^{abbreviation} ', re.IGNORECASE)
        if r.match(text):
            text = r.sub(f'{full} ', text, 1)
            break

    return text
