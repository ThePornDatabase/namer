import unittest
from namer_types import FileNameParts, LookedUpFileInfo, Performer
from types import SimpleNamespace
import re


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
    match = re.search(r'(?P<site>[a-zA-Z0-9]+)[\.\- ]+(?P<year>[0-9]{2}(?:[0-9]{2})?)[\.\- ]+(?P<month>[0-9]{2})[\.\- ]+(?P<day>[0-9]{2})[\.\- ]+(?P<name>.*)\.(?P<ext>[a-zA-Z0-9]{3,4})$',filename)
    parts = FileNameParts()
    if match:
        prefix = "20" if len(match.group('year'))==2 else ""
        parts.date = prefix+match.group('year')+"-"+match.group('month')+"-"+match.group('day')
        name_act_tuple = name_cleaner(match.group('name'))
        parts.name = name_act_tuple[0]
        parts.act = name_act_tuple[1]
        parts.site = match.group('site')
        parts.extension = match.group('ext')
        parts.source_file_name = filename
        return parts

class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    def test_parse_file_name(self):
        name = parse_file_name('EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4')
        self.assertEqual(name.site, "EvilAngel")
        self.assertEqual(name.date, "2022-01-03")
        self.assertEqual(name.name, "Carmela Clutch Fabulous Anal 3-Way")
        self.assertEqual(name.act, None)
        self.assertEqual(name.extension, "mp4")

    def test_parse_file_name_with_act_1(self):
        name = parse_file_name('EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.act.1.XXX.2160p.mp4')
        self.assertEqual(name.site, "EvilAngel")
        self.assertEqual(name.date, "2022-01-03")
        self.assertEqual(name.name, "Carmela Clutch Fabulous Anal 3-Way")
        self.assertEqual(name.act, "act 1")
        self.assertEqual(name.extension, "mp4")

    def test_parse_file_name_with_part_1(self):
        name = parse_file_name('EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.part-1.720p.mp4')
        self.assertEqual(name.site, "EvilAngel")
        self.assertEqual(name.date, "2022-01-03")
        self.assertEqual(name.name, "Carmela Clutch Fabulous Anal 3-Way")
        self.assertEqual(name.act, "part-1")
        self.assertEqual(name.extension, "mp4")

    def test_parse_file_name_with_part1(self):
        name = parse_file_name('EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.part-1-XXX.mp4')
        self.assertEqual(name.site, "EvilAngel")
        self.assertEqual(name.date, "2022-01-03")
        self.assertEqual(name.name, "Carmela Clutch Fabulous Anal 3-Way")
        self.assertEqual(name.act, "part-1")
        self.assertEqual(name.extension, "mp4") 

if __name__ == '__main__':
    unittest.main()
