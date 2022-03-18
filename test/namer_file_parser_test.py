"""
Tests for namer_file_parser.py
"""
import io
import unittest
from unittest.mock import patch
from namer.filenameparser import main, parse_file_name

regex_token = '{_site}{_sep}{_date}{_sep}{_ts}{_name}{_dot}{_ext}'

class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """


    def test_parse_file_name(self):
        """
        Test standard name parsing.
        """
        name = parse_file_name('EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4', regex_token)
        self.assertEqual(name.site, "EvilAngel")
        self.assertEqual(name.date, "2022-01-03")
        self.assertEqual(name.name, "Carmela Clutch Fabulous Anal 3-Way")
        self.assertEqual(name.act, None)
        self.assertEqual(name.trans, False)
        self.assertEqual(name.extension, "mp4")

    def test_parse_clean_file_name(self):
        """
        Test standard name parsing.
        """
        name = parse_file_name('Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way.XXX.mp4', regex_token)
        self.assertEqual(name.site, "EvilAngel")
        self.assertEqual(name.date, "2022-01-03")
        self.assertEqual(name.name, "Carmela Clutch Fabulous Anal 3-Way")
        self.assertEqual(name.act, None)
        self.assertEqual(name.trans, False)
        self.assertEqual(name.extension, "mp4")

    def test_parse_file_name_with_trans(self):
        """
        Test parsing a name with a TS tag after the date, uncommon, but not unheard of.
        """
        name = parse_file_name('EvilAngel.22.01.03.TS.Carmela.Clutch.Fabulous.Anal.3-Way.part-1-XXX.mp4', regex_token)
        self.assertEqual(name.site, "EvilAngel")
        self.assertEqual(name.date, "2022-01-03")
        self.assertEqual(name.name, "Carmela Clutch Fabulous Anal 3-Way part-1")
        self.assertEqual(name.act, None)
        self.assertEqual(name.trans, True)
        self.assertEqual(name.extension, "mp4")

    def test_parse_file_name_complex_site(self):
        """
        Test parsing a name with a TS tag after the date, uncommon, but not unheard of.
        """
        name = parse_file_name('Twistys Feature Film.16.04.07.aidra.fox.the.getaway.part.1.mp4', regex_token)
        self.assertEqual(name.site, "TwistysFeatureFilm")
        self.assertEqual(name.date, "2016-04-07")
        self.assertEqual(name.name, "aidra fox the getaway part 1")
        self.assertEqual(name.act, None)
        self.assertEqual(name.trans, False)
        self.assertEqual(name.extension, "mp4")

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_method(self, mock_stdout):
        """
        Test the main method.
        """
        main(arglist=['-f','EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4'])
        self.assertIn("site: EvilAngel", mock_stdout.getvalue())

if __name__ == '__main__':
    unittest.main()
