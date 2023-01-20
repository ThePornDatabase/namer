"""
Reads movie.xml of Emby/Jellyfin format in to a LookedUpFileInfo, allowing the metadata to be written in to video
files, or used in renaming the video file (currently only mp4s).
"""
import tempfile
import unittest
from pathlib import Path
from shutil import copytree

from namer.fileinfo import parse_file_name
from namer.metadataapi import match
from namer.moviexml import parse_movie_xml_file, write_movie_xml_file
from namer.comparison_results import Performer
from test.utils import environment


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    def test_parsing_xml_metadata(self):
        """
        verify tag in place functions.
        """

        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            copytree(Path(__file__).resolve().parent, tempdir / "test")
            xmlfile = tempdir / "test" / "ea.nfo"
            info = parse_movie_xml_file(xmlfile)
            self.assertEqual(info.site, "Evil Angel")
            self.assertEqual(info.date, "2022-01-03")
            self.assertIsNotNone(info.description)
            if info.description is not None:
                self.assertIn("Cute brunette Carmela Clutch positions her", info.description)
            self.assertEqual(info.look_up_site_id, "https://www.evilangel.com/en/video/0/198543/")
            self.assertEqual(info.uuid, "1678283")
            self.assertEqual(info.name, "Carmela Clutch: Fabulous Anal 3-Way!")
            self.assertIn("Deep Throat", info.tags)
            expected_performers = [
                Performer("Carmela Clutch", "Female"),
                Performer("Francesca Le", "Female"),
                Performer("Mark Wood", "Male")
            ]
            self.assertListEqual(info.performers, expected_performers)

    def test_writing_xml_metadata_genre_flag(self):
        """
        Test parsing a stored response as a LookedUpFileInfo
        """

        with environment() as (_path, fakeTPDB, config):
            name = parse_file_name("EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4", config)
            config.enable_metadataapi_genres = True
            results = match(name, config)
            self.assertEqual(len(results.results), 1)
            result = results.results[0]
            output = write_movie_xml_file(result.looked_up, config)
            expected = f"""<?xml version="1.0" encoding="UTF-8"?>
<movie>
  <plot>Cute brunette Carmela Clutch positions her big, juicy ass for famed director/cocksman Mark Wood's camera to ogle. The well-endowed babe teases, flaunting her voluptuous jugs and derriere. Mark's sexy MILF partner, Francesca Le, finds a 'nice warm place' for her tongue and serves Carmela a lesbian rim job. Francesca takes a labia-licking face ride from the busty babe. Francesca takes over the camera as Mark takes over Carmela's hairy snatch, his big cock ram-fucking her twat. Carmela sucks Mark's meat in a lewd blowjob. Carmela jerks her clit as Mark delivers a vigorous anal pounding! With Mark's prick shoved up her ass, off-screen Francesca orders, 'Keep that pussy busy!' Carmela's huge boobs jiggle as she takes a rectal reaming and buzzes a vibrator on her clit at the same time. Francesca jumps in to make it a threesome, trading ass-to-mouth flavor with the young tramp. This ribald romp reaches its climax as Mark drops a messy, open-mouth cum facial onto Carmela. She lets the jizz drip from her lips, licking the mess from her fingers and rubbing it onto her robust melons.</plot>
  <outline/>
  <title>Carmela Clutch: Fabulous Anal 3-Way!</title>
  <dateadded/>
  <trailer>https://trailers-fame.gammacdn.com/6/7/6/5/c85676/trailers/85676_01/tr_85676_01_1080p.mp4</trailer>
  <year>2022</year>
  <premiered>2022-01-03</premiered>
  <releasedate>2022-01-03</releasedate>
  <mpaa>XXX</mpaa>
  <art>
    <poster>{fakeTPDB.get_url()}qWAUIAUpBsoqKUwozc4NOTR1tPI=/1000x1500/smart/filters:sharpen():upscale():watermark(https%3A%2F%2Fcdn.metadataapi.net%2Fsites%2F3f%2F9f%2F51%2Fcf3828d65425bca2890d53ef242d8cf%2Flogo%2Fevil-angel_dark%5B1%5D.png,-10,-10,25,50)/https%3A%2F%2Fcdn.metadataapi.net%2Fscene%2Ff4%2Fab%2F3e%2Fa91d31d6dee223f4f30a57bfd83b151%2Fbackground%2Fbg-evil-angel-carmela-clutch-fabulous-anal-3-way.webp</poster>
    <background>{fakeTPDB.get_url()}gAu-1j1ZP4f6gNMPibgAyGKoa_c=/fit-in/3000x3000/smart/filters:sharpen():upscale()/https%3A%2F%2Fcdn.metadataapi.net%2Fscene%2Ff4%2Fab%2F3e%2Fa91d31d6dee223f4f30a57bfd83b151%2Fbackground%2Fbg-evil-angel-carmela-clutch-fabulous-anal-3-way.webp</background>
  </art>
  <genre>Anal</genre>
  <genre>Ass</genre>
  <genre>Assorted Additional Tags</genre>
  <genre>Atm</genre>
  <genre>Big Boobs</genre>
  <genre>Big Dick</genre>
  <genre>Blowjob</genre>
  <genre>Brunette</genre>
  <genre>Bubble Butt</genre>
  <genre>Cunnilingus</genre>
  <genre>Deepthroat</genre>
  <genre>Face Sitting</genre>
  <genre>Facial</genre>
  <genre>Fingering</genre>
  <genre>Hairy Pussy</genre>
  <genre>Handjob</genre>
  <genre>Hardcore</genre>
  <genre>Latina</genre>
  <genre>Milf</genre>
  <genre>Pussy To Mouth</genre>
  <genre>Rimming</genre>
  <genre>Sex</genre>
  <genre>Swallow</genre>
  <genre>Threesome</genre>
  <studio>Evil Angel</studio>
  <theporndbid>scenes/1678283</theporndbid>
  <theporndbguid>77fae2fd-cf47-4232-ae04-1ffbc7886ba6</theporndbguid>
  <phoenixadultid/>
  <phoenixadulturlid/>
  <phash/>
  <sourceid>https://evilangel.com/en/video/Carmela-Clutch-Fabulous-Anal-3-Way/198543</sourceid>
  <actor>
    <type>Actor</type>
    <name>Carmela Clutch</name>
    <role>Female</role>
    <image>{fakeTPDB.get_url()}flLf1pecTlKcpJCki30l5iWXNdQ=/1000x1500/smart/filters:sharpen():upscale()/https%3A%2F%2Fcdn.metadataapi.net%2Fperformer%2F3e%2Fb6%2F0a%2F9a33557155b8a6f3e6c88bee8ed65a6%2Fposter%2F6a00376cbee2aa83c8c2514b89b332276df42c35</image>
    <thumb/>
  </actor>
  <actor>
    <type>Actor</type>
    <name>Francesca Le</name>
    <role>Female</role>
    <image>{fakeTPDB.get_url()}r8g92zymZ6SduikMTwcXMojRxik=/1000x1500/smart/filters:sharpen():upscale()/https%3A%2F%2Fcdn.metadataapi.net%2Fperformer%2F71%2F51%2Fdc%2F4b09a05007ba30c041e474c2b398a51%2Fposter%2Ffrancesca-le.png</image>
    <thumb/>
  </actor>
  <actor>
    <type>Actor</type>
    <name>Mark Wood</name>
    <role>Male</role>
    <image>{fakeTPDB.get_url()}EIsvo6fVYUuLzp6bO8I0LYUdZmI=/1000x1500/smart/filters:sharpen():upscale()/https%3A%2F%2Fcdn.metadataapi.net%2Fperformer%2F9d%2Fd5%2F61%2F11eb0285e2534a949839a1a5573be08%2Fposter%2F0955f0ee0c6500c8e17f8dd3cf1a019b6f4d3d3e</image>
    <thumb/>
  </actor>
  <fileinfo/>
</movie>
"""  # noqa: E501
        self.assertEqual(output, expected)

    def test_writing_xml_metadata(self):
        """
        Test parsing a stored response as a LookedUpFileInfo
        """
        with environment() as (_path, fakeTPDB, config):
            name = parse_file_name("EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4", config)
            results = match(name, config)
            self.assertEqual(len(results.results), 1)
            result = results.results[0]
            output = write_movie_xml_file(result.looked_up, config)
            print(output)
            expected = f"""<?xml version="1.0" encoding="UTF-8"?>
<movie>
  <plot>Cute brunette Carmela Clutch positions her big, juicy ass for famed director/cocksman Mark Wood's camera to ogle. The well-endowed babe teases, flaunting her voluptuous jugs and derriere. Mark's sexy MILF partner, Francesca Le, finds a 'nice warm place' for her tongue and serves Carmela a lesbian rim job. Francesca takes a labia-licking face ride from the busty babe. Francesca takes over the camera as Mark takes over Carmela's hairy snatch, his big cock ram-fucking her twat. Carmela sucks Mark's meat in a lewd blowjob. Carmela jerks her clit as Mark delivers a vigorous anal pounding! With Mark's prick shoved up her ass, off-screen Francesca orders, 'Keep that pussy busy!' Carmela's huge boobs jiggle as she takes a rectal reaming and buzzes a vibrator on her clit at the same time. Francesca jumps in to make it a threesome, trading ass-to-mouth flavor with the young tramp. This ribald romp reaches its climax as Mark drops a messy, open-mouth cum facial onto Carmela. She lets the jizz drip from her lips, licking the mess from her fingers and rubbing it onto her robust melons.</plot>
  <outline/>
  <title>Carmela Clutch: Fabulous Anal 3-Way!</title>
  <dateadded/>
  <trailer>https://trailers-fame.gammacdn.com/6/7/6/5/c85676/trailers/85676_01/tr_85676_01_1080p.mp4</trailer>
  <year>2022</year>
  <premiered>2022-01-03</premiered>
  <releasedate>2022-01-03</releasedate>
  <mpaa>XXX</mpaa>
  <art>
    <poster>{fakeTPDB.get_url()}qWAUIAUpBsoqKUwozc4NOTR1tPI=/1000x1500/smart/filters:sharpen():upscale():watermark(https%3A%2F%2Fcdn.metadataapi.net%2Fsites%2F3f%2F9f%2F51%2Fcf3828d65425bca2890d53ef242d8cf%2Flogo%2Fevil-angel_dark%5B1%5D.png,-10,-10,25,50)/https%3A%2F%2Fcdn.metadataapi.net%2Fscene%2Ff4%2Fab%2F3e%2Fa91d31d6dee223f4f30a57bfd83b151%2Fbackground%2Fbg-evil-angel-carmela-clutch-fabulous-anal-3-way.webp</poster>
    <background>{fakeTPDB.get_url()}gAu-1j1ZP4f6gNMPibgAyGKoa_c=/fit-in/3000x3000/smart/filters:sharpen():upscale()/https%3A%2F%2Fcdn.metadataapi.net%2Fscene%2Ff4%2Fab%2F3e%2Fa91d31d6dee223f4f30a57bfd83b151%2Fbackground%2Fbg-evil-angel-carmela-clutch-fabulous-anal-3-way.webp</background>
  </art>
  <tag>Anal</tag>
  <tag>Ass</tag>
  <tag>Assorted Additional Tags</tag>
  <tag>Atm</tag>
  <tag>Big Boobs</tag>
  <tag>Big Dick</tag>
  <tag>Blowjob</tag>
  <tag>Brunette</tag>
  <tag>Bubble Butt</tag>
  <tag>Cunnilingus</tag>
  <tag>Deepthroat</tag>
  <tag>Face Sitting</tag>
  <tag>Facial</tag>
  <tag>Fingering</tag>
  <tag>Hairy Pussy</tag>
  <tag>Handjob</tag>
  <tag>Hardcore</tag>
  <tag>Latina</tag>
  <tag>Milf</tag>
  <tag>Pussy To Mouth</tag>
  <tag>Rimming</tag>
  <tag>Sex</tag>
  <tag>Swallow</tag>
  <tag>Threesome</tag>
  <genre>Adult</genre>
  <studio>Evil Angel</studio>
  <theporndbid>scenes/1678283</theporndbid>
  <theporndbguid>77fae2fd-cf47-4232-ae04-1ffbc7886ba6</theporndbguid>
  <phoenixadultid/>
  <phoenixadulturlid/>
  <phash/>
  <sourceid>https://evilangel.com/en/video/Carmela-Clutch-Fabulous-Anal-3-Way/198543</sourceid>
  <actor>
    <type>Actor</type>
    <name>Carmela Clutch</name>
    <role>Female</role>
    <image>{fakeTPDB.get_url()}flLf1pecTlKcpJCki30l5iWXNdQ=/1000x1500/smart/filters:sharpen():upscale()/https%3A%2F%2Fcdn.metadataapi.net%2Fperformer%2F3e%2Fb6%2F0a%2F9a33557155b8a6f3e6c88bee8ed65a6%2Fposter%2F6a00376cbee2aa83c8c2514b89b332276df42c35</image>
    <thumb/>
  </actor>
  <actor>
    <type>Actor</type>
    <name>Francesca Le</name>
    <role>Female</role>
    <image>{fakeTPDB.get_url()}r8g92zymZ6SduikMTwcXMojRxik=/1000x1500/smart/filters:sharpen():upscale()/https%3A%2F%2Fcdn.metadataapi.net%2Fperformer%2F71%2F51%2Fdc%2F4b09a05007ba30c041e474c2b398a51%2Fposter%2Ffrancesca-le.png</image>
    <thumb/>
  </actor>
  <actor>
    <type>Actor</type>
    <name>Mark Wood</name>
    <role>Male</role>
    <image>{fakeTPDB.get_url()}EIsvo6fVYUuLzp6bO8I0LYUdZmI=/1000x1500/smart/filters:sharpen():upscale()/https%3A%2F%2Fcdn.metadataapi.net%2Fperformer%2F9d%2Fd5%2F61%2F11eb0285e2534a949839a1a5573be08%2Fposter%2F0955f0ee0c6500c8e17f8dd3cf1a019b6f4d3d3e</image>
    <thumb/>
  </actor>
  <fileinfo/>
</movie>
"""  # noqa: E501
        self.assertEqual(output, expected)


if __name__ == "__main__":
    unittest.main()
