"""
Tests for namer_file_parser.py
"""
import io
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from namer.filenameparts import parse_file_name
from namer.command import make_command
from test.utils import environment

REGEX_TOKEN = "{_site}{_sep}{_optional_date}{_ts}{_name}{_dot}{_ext}"


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    def test_parse_file_name(self):
        """
        Test standard name parsing.
        """
        name = parse_file_name("EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4", REGEX_TOKEN)
        self.assertEqual(name.site, "EvilAngel")
        self.assertEqual(name.date, "2022-01-03")
        self.assertEqual(name.name, "Carmela Clutch Fabulous Anal 3-Way")
        self.assertEqual(name.trans, False)
        self.assertEqual(name.extension, "mp4")

    def test_parse_file_name_interesting_site(self):
        """
        Test standard name parsing.
        """
        name = parse_file_name("Mommy's Girl - 15.04.20 - BTS-Mommy Takes a Squirt.mp4", REGEX_TOKEN)
        self.assertEqual(name.site, "Mommy's Girl")
        self.assertEqual(name.date, "2015-04-20")
        self.assertEqual(name.name, "BTS-Mommy Takes a Squirt")
        self.assertEqual(name.trans, False)
        self.assertEqual(name.extension, "mp4")

    def test_parse_file_name_no_date(self):
        """
        Test standard name parsing.
        """
        name = parse_file_name("EvilAngel.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4", REGEX_TOKEN)
        self.assertEqual(name.site, "EvilAngel")
        self.assertEqual(name.date, None)
        self.assertEqual(name.name, "Carmela Clutch Fabulous Anal 3-Way")
        self.assertEqual(name.trans, False)
        self.assertEqual(name.extension, "mp4")

    def test_parse_file_name_no_date_ts_stamp(self):
        """
        Test standard name parsing.
        """
        name = parse_file_name("EvilAngel.TS.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4", REGEX_TOKEN)
        self.assertEqual(name.site, "EvilAngel")
        self.assertEqual(name.date, None)
        self.assertEqual(name.name, "Carmela Clutch Fabulous Anal 3-Way")
        self.assertEqual(name.trans, True)
        self.assertEqual(name.extension, "mp4")

    def test_parse_clean_file_name(self):
        """
        Test standard name parsing.
        """
        name = parse_file_name("Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way.XXX.mp4", REGEX_TOKEN)
        self.assertEqual(name.site, "Evil Angel")
        self.assertEqual(name.date, "2022-01-03")
        self.assertEqual(name.name, "Carmela Clutch Fabulous Anal 3-Way")
        self.assertEqual(name.trans, False)
        self.assertEqual(name.extension, "mp4")

    def test_parse_file_name_with_trans(self):
        """
        Test parsing a name with a TS tag after the date, uncommon, but not unheard of.
        """
        name = parse_file_name("EvilAngel.22.01.03.TS.Carmela.Clutch.Fabulous.Anal.3-Way.part-1-XXX.mp4", REGEX_TOKEN)
        self.assertEqual(name.site, "EvilAngel")
        self.assertEqual(name.date, "2022-01-03")
        self.assertEqual(name.name, "Carmela Clutch Fabulous Anal 3-Way part-1")
        self.assertEqual(name.trans, True)
        self.assertEqual(name.extension, "mp4")

    def test_parse_file_name_complex_site(self):
        """
        Test parsing a name with a TS tag after the date, uncommon, but not unheard of.
        """
        name = parse_file_name("Twistys Feature Film.16.04.07.aidra.fox.the.getaway.part.1.mp4", REGEX_TOKEN)
        self.assertEqual(name.site, "Twistys Feature Film")
        self.assertEqual(name.date, "2016-04-07")
        self.assertEqual(name.name, "aidra fox the getaway part 1")
        self.assertEqual(name.trans, False)
        self.assertEqual(name.extension, "mp4")

    def test_parse_file_name_c_site(self):
        """
        Test parsing a name with a TS tag after the date, uncommon, but not unheard of.
        """
        name = parse_file_name("BrazzersExxtra - 2021-12-07 - Dr. Polla & The Chronic Discharge Conundrum.mp4", REGEX_TOKEN)
        self.assertEqual(name.site, "BrazzersExxtra")
        self.assertEqual(name.date, "2021-12-07")
        self.assertEqual(name.name, "Dr  Polla & The Chronic Discharge Conundrum")
        self.assertEqual(name.trans, False)
        self.assertEqual(name.extension, "mp4")

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_parse_file(self, mock_stdout):
        """
        Test the main method.
        """
        with environment() as (tmpdir, _parrot, config):
            tempdir = Path(tmpdir)
            test_dir = Path(__file__).resolve().parent
            target_file = (tempdir / "EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4")
            shutil.copy(test_dir / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4", target_file)
            config.min_file_size = 0
            command = make_command(target_file, config)
            self.assertIsNotNone(command)
            if command is not None:
                self.assertIsNotNone(command.parsed_file)
                if command.parsed_file is not None:
                    self.assertEqual(command.parsed_file.site, "EvilAngel")
                    self.assertEqual(command.parsed_file.date, "2022-01-03")
                    self.assertEqual(command.parsed_file.name, "Carmela Clutch Fabulous Anal 3-Way")
                    self.assertEqual(command.parsed_file.trans, False)
                    self.assertEqual(command.parsed_file.extension, "mp4")

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_parse_dir_name(self, mock_stdout):
        """
        Test the main method.
        """
        with environment() as (tmpdir, _parrot, config):
            tempdir = Path(tmpdir)
            test_dir = Path(__file__).resolve().parent
            target_file = (tempdir / "EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX" / "EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4")
            target_file.parent.mkdir()
            shutil.copy(test_dir / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4", target_file)
            config.min_file_size = 0
            config.prefer_dir_name_if_available = True
            command = make_command(target_file.parent, config)
            self.assertIsNotNone(command)
            if command is not None:
                self.assertIsNotNone(command.parsed_file)
                if command.parsed_file is not None:
                    self.assertEqual(command.parsed_file.site, "EvilAngel")
                    self.assertEqual(command.parsed_file.date, "2022-01-03")
                    self.assertEqual(command.parsed_file.name, "Carmela Clutch Fabulous Anal 3-Way")
                    self.assertEqual(command.parsed_file.trans, False)
                    self.assertEqual(command.parsed_file.extension, "mp4")


if __name__ == "__main__":
    unittest.main()
