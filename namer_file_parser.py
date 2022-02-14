"""
Parse string in to FileNamePart define in namer_types.
"""
import logging
import re
import sys
from namer_types import FileNameParts


def name_cleaner(name: str):
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
    match = re.search(r'(?P<name>.+)[\.\- ](?P<part>[p|P][a|A][r|R][t|T][\.\- ]{0,1}[0-9]+){0,1}' +
        r'(?P<act>[a|A][c|C][t|T][\.\- ]{0,1}[0-9]+){0,1}[\.\- ]*$',name)
    act = None
    if match:
        if match.group('act') is not None:
            act = match.group('act')
        if match.group('part') is not None:
            act = match.group('part')
        if act is not None:
            name = match.group('name')
    return (name, act)


def parse_file_name(filename: str) -> FileNameParts:
    """
    Given an input name of the form site-yy.mm.dd-some.name.part.1.XXX.2160p.mp4,
    parses out the relevant information in to a structure form.
    """
    match = re.search(r'(?P<site>[a-zA-Z0-9]+)[\.\- ]+(?P<year>[0-9]{2}(?:[0-9]{2})?)[\.\- ]+' +
                      r'(?P<month>[0-9]{2})[\.\- ]+(?P<day>[0-9]{2})[\.\- ]+' +
                      r'((?P<trans>[T|t][S|s])[\.\- ]+){0,1}(?P<name>.*)\.(?P<ext>[a-zA-Z0-9]{3,4})$',filename)
    file_name_parts = FileNameParts()
    if match:
        prefix = "20" if len(match.group('year'))==2 else ""
        file_name_parts.date = prefix+match.group('year')+"-"+match.group('month')+"-"+match.group('day')
        name_act_tuple = name_cleaner(match.group('name'))
        file_name_parts.name = name_act_tuple[0]
        file_name_parts.act = name_act_tuple[1]
        file_name_parts.site = match.group('site')
        trans = match.group('trans')
        file_name_parts.trans = (not trans is None) and (trans.strip().upper() == 'TS')
        file_name_parts.extension = match.group('ext')
        file_name_parts.source_file_name = filename
        return file_name_parts
    logging.warning("Could not parse file name: %s", filename)
    return None


def usage():
    """
    Help messages for the main method.
    """
    print("You are using the file name parser of the Namer project")
    print("Expects a single input, and will output the contents of FileNameParts, is the internal input")
    print("to the namer_metadatapi.py script.")
    print("Output will be the representation of that FileNameParts.")


if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1].strip().upper() == '-H':
        usage()
    else:
        parts = parse_file_name(sys.argv[1])
        print(parts)
