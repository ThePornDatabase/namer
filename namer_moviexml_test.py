"""
Reads movie.xml of Emby/Jellyfin format in to a LookedUpFileInfo, allowing the metadata to be written in to video
files, or used in renaming the video file (currently only mp4s).
"""
from pathlib import Path
import unittest
import tempfile
from namer_moviexml import parse_movie_xml_file
from namer_dirscanner_test import prepare_workdir
from namer_types import Performer

class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    def test_writing_metadata(self):
        """
        verify tag in place functions.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(prepare_workdir(tmpdir))
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


if __name__ == '__main__':
    unittest.main()
