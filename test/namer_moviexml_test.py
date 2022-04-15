"""
Reads movie.xml of Emby/Jellyfin format in to a LookedUpFileInfo, allowing the metadata to be written in to video
files, or used in renaming the video file (currently only mp4s).
"""
from pathlib import Path
from shutil import copytree
import unittest
import tempfile
from unittest import mock
from namer.moviexml import parse_movie_xml_file, write_movie_xml_file
from namer.metadataapi import parse_file_name, match
from namer.types import Performer, default_config

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
            self.assertIn('Cute brunette Carmela Clutch positions her', info.description)
            self.assertEqual(info.look_up_site_id, "https://www.evilangel.com/en/video/0/198543/")
            self.assertEqual(info.uuid, '1678283')
            self.assertEqual(info.name, "Carmela Clutch: Fabulous Anal 3-Way!")
            self.assertIn('Deep Throat',info.tags)
            expected_performers = []
            expected_performers.append(Performer("Carmela Clutch", "Female"))
            expected_performers.append(Performer("Francesca Le","Female"))
            expected_performers.append(Performer("Mark Wood","Male"))
            self.assertListEqual(info.performers, expected_performers)

    @mock.patch("namer.metadataapi.__get_response_json_object")
    def test_writing_xml_metadata(self, mock_response):
        """
        Test parsing a stored response as a LookedUpFileInfo
        """
        response = Path(__file__).resolve().parent / "ea.full.json"
        mock_response.return_value = response.read_text()
        name = parse_file_name('EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4')
        results = match(name, default_config())
        self.assertEqual(len(results), 1)
        result = results[0]
        output = write_movie_xml_file(result.looked_up)
        print("Found: \n"+output)



if __name__ == '__main__':
    unittest.main()
