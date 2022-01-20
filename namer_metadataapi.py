import os
import json
import urllib.request
import urllib.parse
import unittest
import tempfile
from namer_types import LookedUpFileInfo, Performer, FileNameParts
from distutils.dir_util import copy_tree
from types import SimpleNamespace
import pathlib
import re
from typing import List

def get_response_json_object(url, authtoken) -> str:
    """
    returns json object with info
    """
    req = urllib.request.Request(url)
    req.add_header("Authorization", "Bearer %s" % authtoken) 
    req.add_header("Content-Type", "application/json") 
    req.add_header("Accept", "application/json") 
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)')

    try:
        with urllib.request.urlopen(req) as response:
            html = response.read()
            return html
    except urllib.error.HTTPError as e:
        print(e)

def get_poster(url: str, authtoken: str, dir: str) -> str:
    """
    returns json object with info
    """
    req = urllib.request.Request(url)
    req.add_header("Authorization", "Bearer %s" % authtoken) 
    #req.add_header("Content-Type", "application/json") 
    #req.add_header("Accept", "application/json") 
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)')

    file = os.path.join(dir, "poster"+pathlib.Path(url).suffix)
    with urllib.request.urlopen(req) as response:
        content = response.read()
        with open(file, "wb") as binary_file:
            # Write bytes to file
            binary_file.write(content)  
    return file         

def metadataapi_response_to_data(json_object, url, json_response, name_parts) -> List[LookedUpFileInfo]:
    fileInfos = []
    for data in json_object.data:
        fileInfo = LookedUpFileInfo()
        fileInfo.name = data.title
        fileInfo.description = data.description
        fileInfo.date = data.date
        fileInfo.source_url = data.url
        fileInfo.poster_url = data.poster
        fileInfo.site = data.site.name
        fileInfo.look_up_site_id = data._id
        for json_performer in data.performers:
            performer = Performer()
            if hasattr(json_performer, "parent") and hasattr(json_performer.parent, "extras"):
                performer.role = json_performer.parent.extras.gender
            performer.name = json_performer.name
            fileInfo.performers.append(performer)
        fileInfo.original_query=url
        fileInfo.original_response=json_response
        fileInfo.original_parsed_filename=name_parts
        fileInfos.append(fileInfo)
    return fileInfos

def buildUrl(site=None, date=None, name=None) -> str:
    #filename = ""
    query = ""
    if site != None:
        query += urllib.parse.quote(re.sub(r' ', '.', site))+"."
    if date != None:
        query += date+"."
    if name != None:
        query += urllib.parse.quote(re.sub(r' ', '.', name))
    return "https://api.metadataapi.net/scenes?q={}&limit=1".format(query)
    

def getMetadataApiNetFileInfo(name_parts: FileNameParts, authtoken: str, skipdate: bool, skipsite: bool, skipname: bool) -> List[LookedUpFileInfo]:
    date = name_parts.date if not skipdate else None
    site = name_parts.site if not skipsite else None
    name = name_parts.name if not skipname else None
    url = buildUrl(site, date, name)
    print("\n\nQuerying: \n{}".format(url))
    json_response = get_response_json_object(url, authtoken)
    json_obj = json.loads(json_response, object_hook=lambda d: SimpleNamespace(**d))
    formatted = json.dumps(json.loads(json_response), indent=4, sort_keys=True)
    fileInfos = metadataapi_response_to_data(json_obj, url, formatted, name_parts)
    return fileInfos

class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    current=os.path.dirname(os.path.abspath(__file__))

    def prepare_workdir():
        current=os.path.dirname(os.path.abspath(__file__))
        test_fixture="test"
        tmpdir = tempfile.TemporaryDirectory()
        test_root = os.path.join(tmpdir.name,test_fixture)
        copy_tree(os.path.join(current, test_fixture), tmpdir.name)
        return tmpdir

    def __test_call_metadataapi_net(self):
        tmpdir = UnitTestAsTheDefaultExecution.prepare_workdir()
        url="https://api.metadataapi.net/scenes?parse=EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way&q=Fabulous.Anal.3-Way&limit=5"
        json_object = get_response_json_object(url, "")
        self.assertRegex("Carmela Clutch: Fabulous Anal 3-Way!", json_object.data[0].title)
        self.assertRegex("2022-01-03", json_object.data[0].date)
        self.assertRegex("Evil Angel", json_object.data[0].site.name)
        tmpdir.cleanup()

    def test_parse_response_metadataapi_net(self):
        with open(os.path.join(self.current,"test","response.json"),'r') as days_file:
            json_object = json.loads(days_file.read(), object_hook=lambda d: SimpleNamespace(**d))
            info = metadataapi_response_to_data(json_object, "url", days_file.read(), [])[0]
            self.assertEqual(info.name, "Carmela Clutch: Fabulous Anal 3-Way!")
            self.assertEqual(info.date, "2022-01-03")
            self.assertEqual(info.site, "Evil Angel")
            self.assertRegex(info.description, r'brunette Carmela Clutch positions her big, juicy')
            self.assertEqual(info.source_url, "https://evilangel.com/en/video/Carmela-Clutch-Fabulous-Anal-3-Way/198543")
            self.assertEqual(info.poster_url, "https://thumb.metadataapi.net/unsafe/1000x1500/smart/filters:sharpen():upscale()/https%3A%2F%2Fcdn.metadataapi.net%2Fscene%2Fe6%2Fb9%2F5b%2F066589730107dcfd6b656a398a584b5%2Fbackground%2Fbg-evil-angel-carmela-clutch-fabulous-anal-3-way.jpg")
            expected = []
            expected.append(Performer("Carmela Clutch", "Female"))
            expected.append(Performer("Francesca Le","Female"))
            expected.append(Performer("Mark Wood","Male"))     
            self.assertListEqual(info.performers, expected)


    def test_parse_response_metadataapi_net_dorcel(self):
        with open(os.path.join(self.current,"test","DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.json"),'r') as days_file:
            json_object = json.loads(days_file.read(), object_hook=lambda d: SimpleNamespace(**d))
            info = metadataapi_response_to_data(json_object, "url", days_file.read(), [])[0]
            self.assertEqual(info.name, "Peeping Tom")
            self.assertEqual(info.date, "2021-12-23")
            self.assertEqual(info.site, "Dorcel Club")
            self.assertRegex(info.description, r'kissing in a parking lot')
            self.assertEqual(info.source_url, "https://dorcelclub.com/en/scene/85289/peeping-tom")
            self.assertEqual(info.poster_url, "https://thumb.metadataapi.net/unsafe/1000x1500/smart/filters:sharpen():upscale():watermark(https%3A%2F%2Fcdn.metadataapi.net%2Fsites%2F15%2Fe1%2Fac%2Fe028ae39fdc24d6d0fed4ecf14e53ae%2Flogo%2Fdorcelclub-logo.png,-10,-10,25)/https%3A%2F%2Fcdn.metadataapi.net%2Fscene%2F6e%2Fca%2F89%2F05343d45d85ef2d480ed63f6311d229%2Fbackground%2Fbg-dorcel-club-peeping-tom.jpg")
            expected = []
            expected.append(Performer("Ryan Benetti", None))
            expected.append(Performer("Aya Benetti","Female"))
            expected.append(Performer("Bella Tina","Female"))     
            expected.append(Performer("Megane Lopez","Female"))     
            self.assertListEqual(info.performers, expected)

if __name__ == '__main__':
    unittest.main()