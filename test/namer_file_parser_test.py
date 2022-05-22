"""
Tests for namer_file_parser.py
"""
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from namer.fileexplorer import attempt_analyze, main
from namer.filenameparser import parse_file_name
from test.utils import sample_config

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
        filename: str = 'EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4'
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            with open((tempdir / filename), 'w'):
                pass
            config = sample_config()
            config.min_file_size = 0
            name = attempt_analyze((tempdir / filename), config)
            self.assertIsNotNone(name)
            if name is not None:
                self.assertIsNotNone(name.parsed_file)
                if name.parsed_file is not None:
                    self.assertEqual(name.parsed_file.site, "EvilAngel")
                    self.assertEqual(name.parsed_file.date, "2022-01-03")
                    self.assertEqual(name.parsed_file.name, "Carmela Clutch Fabulous Anal 3-Way")
                    self.assertEqual(name.parsed_file.trans, False)
                    self.assertEqual(name.parsed_file.extension, "mp4")

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_parse_dir_name(self, mock_stdout):
        """
        Test the main method.
        """
        filename: str = 'EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX'
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            target_file = tempdir / filename / "sample.mp4"
            target_file.parent.mkdir()
            with open(target_file, 'w'):
                pass
            config = sample_config()
            config.min_file_size = 0
            config.prefer_dir_name_if_available = True
            name = attempt_analyze(target_file.parent, config)
            self.assertIsNotNone(name)
            if name is not None:
                self.assertIsNotNone(name.parsed_file)
                if name.parsed_file is not None:
                    self.assertEqual(name.parsed_file.site, "EvilAngel")
                    self.assertEqual(name.parsed_file.date, "2022-01-03")
                    self.assertEqual(name.parsed_file.name, "Carmela Clutch Fabulous Anal 3-Way")
                    self.assertEqual(name.parsed_file.trans, False)
                    self.assertEqual(name.parsed_file.extension, "mp4")

    @patch("sys.stdout", new_callable=io.StringIO)
    @patch("namer.fileexplorer.default_config")
    def test_main_method(self, config_mock, mock_stdout):
        """
        Test the main method.
        """
        config = sample_config()
        config.min_file_size = 0
        config_mock.side_effect = [config]
        filename: str = 'EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4'
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            target = (tempdir / filename)
            with open(target, 'w'):
                pass
            main(arg_list=["-f", str(target)])
            self.assertIn("site: EvilAngel", mock_stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
