"""
Reads movie.xml of Emby/Jellyfin format in to a LookedUpFileInfo, allowing the metadata to be written in to video
files, or used in renaming the video file (currently only mp4s).
"""
import tempfile
import unittest
from pathlib import Path
from shutil import copytree
from unittest import mock

from namer.filenameparts import parse_file_name
from namer.metadataapi import match
from namer.moviexml import parse_movie_xml_file, write_movie_xml_file
from namer.comparison_results import Performer
from test.utils import sample_config


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

    @mock.patch("namer.metadataapi.__get_response_json_object")
    def test_writing_xml_metadata_genre_flag(self, mock_response):
        """
        Test parsing a stored response as a LookedUpFileInfo
        """
        response = Path(__file__).resolve().parent / "ea.full.json"
        mock_response.return_value = response.read_text()
        name = parse_file_name("EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4")
        config = sample_config()
        config.enable_metadataapi_genres = True
        results = match(name, config)
        self.assertEqual(len(results.results), 1)
        result = results.results[0]
        output = write_movie_xml_file(result.looked_up, config)
        expected = """<?xml version='1.0' encoding='UTF-8'?>
<movie>
  <plot>Cute brunette Carmela Clutch positions her big, juicy ass for famed director/cocksman Mark Wood's camera to ogle. The well-endowed babe teases, flaunting her voluptuous jugs and derriere. Mark's sexy MILF partner, Francesca Le, finds a 'nice warm place' for her tongue and serves Carmela a lesbian rim job. Francesca takes a labia-licking face ride from the busty babe. Francesca takes over the camera as Mark takes over Carmela's hairy snatch, his big cock ram-fucking her twat. Carmela sucks Mark's meat in a lewd blowjob. Carmela jerks her clit as Mark delivers a vigorous anal pounding! With Mark's prick shoved up her ass, off-screen Francesca orders, 'Keep that pussy busy!' Carmela's huge boobs jiggle as she takes a rectal reaming and buzzes a vibrator on her clit at the same time. Francesca jumps in to make it a threesome, trading ass-to-mouth flavor with the young tramp. This ribald romp reaches its climax as Mark drops a messy, open-mouth cum facial onto Carmela. She lets the jizz drip from her lips, licking the mess from her fingers and rubbing it onto her robust melons.</plot>
  <outline/>
  <title>Carmela Clutch: Fabulous Anal 3-Way!</title>
  <dateadded/>
  <trailer/>
  <year>2022</year>
  <premiered>2022-01-03</premiered>
  <releasedate>2022-01-03</releasedate>
  <mpaa>XXX</mpaa>
  <art>
    <poster/>
    <background/>
  </art>
  <genre>Anal</genre>
  <genre>Ass</genre>
  <genre>Ass to mouth</genre>
  <genre>Big Dick</genre>
  <genre>Blowjob</genre>
  <genre>Blowjob - Double</genre>
  <genre>Brunette</genre>
  <genre>Bubble Butt</genre>
  <genre>Cum swallow</genre>
  <genre>Deepthroat</genre>
  <genre>FaceSitting</genre>
  <genre>Facial</genre>
  <genre>Gonzo / No Story</genre>
  <genre>HD Porn</genre>
  <genre>Hairy Pussy</genre>
  <genre>Handjob</genre>
  <genre>Hardcore</genre>
  <genre>Latina</genre>
  <genre>MILF</genre>
  <genre>Pussy to mouth</genre>
  <genre>Rimming</genre>
  <genre>Sex</genre>
  <genre>Tattoo</genre>
  <genre>Threesome</genre>
  <genre>Toys / Dildos</genre>
  <studio>Evil Angel</studio>
  <theporndbid>1678283</theporndbid>
  <phoenixadultid/>
  <phoenixadulturlid/>
  <sourceid>https://evilangel.com/en/video/Carmela-Clutch-Fabulous-Anal-3-Way/198543</sourceid>
  <actor>
    <name>Carmela Clutch</name>
    <role>Female</role>
    <image>https://thumb.metadataapi.net/unsafe/1000x1500/smart/filters:sharpen():upscale()/https%3A%2F%2Fcdn.metadataapi.net%2Fperformer%2F89%2Fe2%2F75%2Fe552433560b16498362696874a8436e%2Fposter%2Fcarmela-clutch.jpg</image>
    <type>Actor</type>
    <thumb/>
  </actor>
  <actor>
    <name>Francesca Le</name>
    <role>Female</role>
    <image>https://thumb.metadataapi.net/unsafe/1000x1500/smart/filters:sharpen():upscale()/https%3A%2F%2Fcdn.metadataapi.net%2Fperformer%2Fb0%2F3a%2F1a%2F34a769a25d20123f7366cbf93ec1f47%2Fposter%2Ffrancesca-le.jpg</image>
    <type>Actor</type>
    <thumb/>
  </actor>
  <actor>
    <name>Mark Wood</name>
    <role>Male</role>
    <image>https://thumb.metadataapi.net/unsafe/1000x1500/smart/filters:sharpen():upscale()/https%3A%2F%2Fcdn.metadataapi.net%2Fperformer%2F8f%2F6d%2F91%2F6fb5a7c81a0e5c891e2f434698ad5c3%2Fposter%2Fmark-wood.jpg</image>
    <type>Actor</type>
    <thumb/>
  </actor>
  <fileinfo/>
</movie>
"""  # noqa: E501
        self.assertEqual(output, expected)

    @mock.patch("namer.metadataapi.__get_response_json_object")
    def test_writing_xml_metadata(self, mock_response):
        """
        Test parsing a stored response as a LookedUpFileInfo
        """
        response = Path(__file__).resolve().parent / "ea.full.json"
        mock_response.return_value = response.read_text()
        name = parse_file_name("EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4")
        config = sample_config()
        results = match(name, config)
        self.assertEqual(len(results.results), 1)
        result = results.results[0]
        output = write_movie_xml_file(result.looked_up, config)
        expected = """<?xml version='1.0' encoding='UTF-8'?>
<movie>
  <plot>Cute brunette Carmela Clutch positions her big, juicy ass for famed director/cocksman Mark Wood's camera to ogle. The well-endowed babe teases, flaunting her voluptuous jugs and derriere. Mark's sexy MILF partner, Francesca Le, finds a 'nice warm place' for her tongue and serves Carmela a lesbian rim job. Francesca takes a labia-licking face ride from the busty babe. Francesca takes over the camera as Mark takes over Carmela's hairy snatch, his big cock ram-fucking her twat. Carmela sucks Mark's meat in a lewd blowjob. Carmela jerks her clit as Mark delivers a vigorous anal pounding! With Mark's prick shoved up her ass, off-screen Francesca orders, 'Keep that pussy busy!' Carmela's huge boobs jiggle as she takes a rectal reaming and buzzes a vibrator on her clit at the same time. Francesca jumps in to make it a threesome, trading ass-to-mouth flavor with the young tramp. This ribald romp reaches its climax as Mark drops a messy, open-mouth cum facial onto Carmela. She lets the jizz drip from her lips, licking the mess from her fingers and rubbing it onto her robust melons.</plot>
  <outline/>
  <title>Carmela Clutch: Fabulous Anal 3-Way!</title>
  <dateadded/>
  <trailer/>
  <year>2022</year>
  <premiered>2022-01-03</premiered>
  <releasedate>2022-01-03</releasedate>
  <mpaa>XXX</mpaa>
  <art>
    <poster/>
    <background/>
  </art>
  <tag>Anal</tag>
  <tag>Ass</tag>
  <tag>Ass to mouth</tag>
  <tag>Big Dick</tag>
  <tag>Blowjob</tag>
  <tag>Blowjob - Double</tag>
  <tag>Brunette</tag>
  <tag>Bubble Butt</tag>
  <tag>Cum swallow</tag>
  <tag>Deepthroat</tag>
  <tag>FaceSitting</tag>
  <tag>Facial</tag>
  <tag>Gonzo / No Story</tag>
  <tag>HD Porn</tag>
  <tag>Hairy Pussy</tag>
  <tag>Handjob</tag>
  <tag>Hardcore</tag>
  <tag>Latina</tag>
  <tag>MILF</tag>
  <tag>Pussy to mouth</tag>
  <tag>Rimming</tag>
  <tag>Sex</tag>
  <tag>Tattoo</tag>
  <tag>Threesome</tag>
  <tag>Toys / Dildos</tag>
  <genre>Adult</genre>
  <studio>Evil Angel</studio>
  <theporndbid>1678283</theporndbid>
  <phoenixadultid/>
  <phoenixadulturlid/>
  <sourceid>https://evilangel.com/en/video/Carmela-Clutch-Fabulous-Anal-3-Way/198543</sourceid>
  <actor>
    <name>Carmela Clutch</name>
    <role>Female</role>
    <image>https://thumb.metadataapi.net/unsafe/1000x1500/smart/filters:sharpen():upscale()/https%3A%2F%2Fcdn.metadataapi.net%2Fperformer%2F89%2Fe2%2F75%2Fe552433560b16498362696874a8436e%2Fposter%2Fcarmela-clutch.jpg</image>
    <type>Actor</type>
    <thumb/>
  </actor>
  <actor>
    <name>Francesca Le</name>
    <role>Female</role>
    <image>https://thumb.metadataapi.net/unsafe/1000x1500/smart/filters:sharpen():upscale()/https%3A%2F%2Fcdn.metadataapi.net%2Fperformer%2Fb0%2F3a%2F1a%2F34a769a25d20123f7366cbf93ec1f47%2Fposter%2Ffrancesca-le.jpg</image>
    <type>Actor</type>
    <thumb/>
  </actor>
  <actor>
    <name>Mark Wood</name>
    <role>Male</role>
    <image>https://thumb.metadataapi.net/unsafe/1000x1500/smart/filters:sharpen():upscale()/https%3A%2F%2Fcdn.metadataapi.net%2Fperformer%2F8f%2F6d%2F91%2F6fb5a7c81a0e5c891e2f434698ad5c3%2Fposter%2Fmark-wood.jpg</image>
    <type>Actor</type>
    <thumb/>
  </actor>
  <fileinfo/>
</movie>
"""  # noqa: E501
        self.assertEqual(output, expected)


if __name__ == "__main__":
    unittest.main()
