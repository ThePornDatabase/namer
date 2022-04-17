"""
Parse string in to FileNamePart define in namer_types.
"""
import argparse
from pathlib import PurePath
import re
import sys
from typing import List
from loguru import logger
from namer.types import FileNameParts


DEFAULT_REGEX_TOKENS = '{_site}{_sep}{_optional_date}{_ts}{_name}{_dot}{_ext}'

def name_cleaner(name: str) -> str:
    """
    Given the name parts, following a date, but preceding the file extension, attempt to glean
    extra information and discard useless information for matching with the porndb.
    """
    # truncating cruft
    for size in ['2160p', '1080p', '720p', '4k',  '3840p']:
        name = re.sub(r"[\.\- ]"+size+r"[\.\- ]{0,1}.*", "", name)
    # remove trailing ".XXX."
    name = re.sub(r"[\.\- ]{0,1}XXX[\.\- ]{0,1}.*$", "", name)
    name = re.sub(r'\.', ' ', name)
    return name


def parser_config_to_regex(tokens: str) -> str:
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

    _sep=r'[\.\- ]+'
    _site=r'(?P<site>[a-zA-Z0-9\'\.\-\ ]*?[a-zA-Z0-9]*?)'
    _date=r'(?P<year>[0-9]{2}(?:[0-9]{2})?)[\.\- ]+(?P<month>[0-9]{2})[\.\- ]+(?P<day>[0-9]{2})'
    _optional_date=r'(?:(?P<year>[0-9]{2}(?:[0-9]{2})?)[\.\- ]+(?P<month>[0-9]{2})[\.\- ]+(?P<day>[0-9]{2})[\.\- ]+)?'
    _ts=r'((?P<trans>[T|t][S|s])'+_sep+'){0,1}'
    _name=r'(?P<name>(?:.(?![0-9]{2,4}[\.\- ][0-9]{2}[\.\- ][0-9]{2}))*)'
    _dot=r'\.'
    _ext=r'(?P<ext>[a-zA-Z0-9]{3,4})$'
    regex = tokens.format_map(
        {'_site':_site,
        '_date':_date,
        '_optional_date':_optional_date,
        '_ts':_ts,
        '_name':_name,
        '_ext':_ext,
        '_sep':_sep,
        '_dot':_dot}
        )
    return regex


def parse_file_name(filename: str, regex_config: str = DEFAULT_REGEX_TOKENS) -> FileNameParts:
    """
    Given an input name of the form site-yy.mm.dd-some.name.part.1.XXX.2160p.mp4,
    parses out the relevant information in to a structure form.
    """
    regex = parser_config_to_regex(regex_config)
    file_name_parts = FileNameParts()
    file_name_parts.extension = PurePath(filename).suffix[1:]
    match = re.search(regex,filename)
    if match:
        if match.groupdict().get('year') is not None:
            prefix = "20" if len(match.group('year'))==2 else ""
            file_name_parts.date = prefix+match.group('year')+"-"+match.group('month')+"-"+match.group('day')
        if match.groupdict().get('name') is not None:
            file_name_parts.name = name_cleaner(match.group('name'))
        if match.groupdict().get('site') is not None:
            file_name_parts.site = re.sub(r'[\.\-\ ]','',match.group('site'))
        if match.groupdict().get('trans') is not None:
            trans = match.group('trans')
            file_name_parts.trans = (not trans is None) and (trans.strip().upper() == 'TS')
        file_name_parts.extension = match.group('ext')
        file_name_parts.source_file_name = filename
    else:
        logger.warning("Could not parse file name: {filename}")
    return file_name_parts


def main(arglist: List[str]):
    """
    Attempt to parse a name.
    """
    description = ("You are using the file name parser of the Namer project.  " +
        "Expects a single input, and will output the contents of FileNameParts, which is the internal input " +
        "to the namer_metadatapi.py script. "+
        "Output will be the representation of that FileNameParts.\n")
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-f", "--file", help="String to parse for name parts", required=True)
    args = parser.parse_args(arglist)
    print(parse_file_name(args.file, DEFAULT_REGEX_TOKENS))

if __name__ == "__main__":
    main(arglist=sys.argv[1:])
