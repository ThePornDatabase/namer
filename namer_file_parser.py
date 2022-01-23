from namer_types import FileNameParts
import re
import sys


def name_cleaner(name: str):
    #truncating cruft
    for s in ['2160p', '1080p', '720p', '4k',  '3840p']:
        name = re.sub(r"[\.\- ]"+s+"[\.\- ]{0,1}.*", "", name)
    #remove trailing ".XXX."    
    name = re.sub(r"[\.\- ]{0,1}XXX[\.\- ]{0,1}.*$", "", name)
    name = re.sub(r'\.', ' ', name)
    match = re.search(r'(?P<name>.+)[\.\- ](?P<part>[p|P][a|A][r|R][t|T][\.\- ]{0,1}[0-9]+){0,1}(?P<act>[a|A][c|C][t|T][\.\- ]{0,1}[0-9]+){0,1}[\.\- ]*$',name)
    act = None
    if match:
        if match.group('act') != None:
            act = match.group('act')
        if match.group('part') != None:
            act = match.group('part')
        if act != None:
            name = match.group('name')       
    return (name, act)

def parse_file_name(filename: str) -> FileNameParts:
    match = re.search(r'(?P<site>[a-zA-Z0-9]+)[\.\- ]+(?P<year>[0-9]{2}(?:[0-9]{2})?)[\.\- ]+(?P<month>[0-9]{2})[\.\- ]+(?P<day>[0-9]{2})[\.\- ]+((?P<trans>[T|t][S|s])[\.\- ]+){0,1}(?P<name>.*)\.(?P<ext>[a-zA-Z0-9]{3,4})$',filename)
    parts = FileNameParts()
    if match:
        prefix = "20" if len(match.group('year'))==2 else ""
        parts.date = prefix+match.group('year')+"-"+match.group('month')+"-"+match.group('day')
        name_act_tuple = name_cleaner(match.group('name'))
        parts.name = name_act_tuple[0]
        parts.act = name_act_tuple[1]
        parts.site = match.group('site')
        trans = match.group('trans')
        parts.trans = (not trans == None) and (trans.strip().upper() == 'TS')
        parts.extension = match.group('ext')
        parts.source_file_name = filename
        return parts

def usage():
    print("You are using the file name parser of the Namer project")
    print("Expects a single input, and will output the contents of FileNameParts, is the internal input")
    print("to the namer_metadatapi.py script.")
    print("Output will be the representation of that FileNameParts.")

if __name__ == "__main__":
    if (len(sys.argv) == 1 ) or (sys.argv[1].strip().upper() == '-H' ): 
        usage() 
    else:
        parts = parse_file_name(sys.argv[1])
        print(parts)