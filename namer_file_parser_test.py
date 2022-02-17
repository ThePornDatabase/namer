"""
Tests for namer_file_parser.py
"""
import unittest
from namer_file_parser import parse_file_name

class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    def test_parse_file_name(self):
        """
        Test standard name parsing.
        """
        name = parse_file_name('EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4')
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
        name = parse_file_name('Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way.XXX.mp4')
        self.assertEqual(name.site, "EvilAngel")
        self.assertEqual(name.date, "2022-01-03")
        self.assertEqual(name.name, "Carmela Clutch Fabulous Anal 3-Way")
        self.assertEqual(name.act, None)
        self.assertEqual(name.trans, False)
        self.assertEqual(name.extension, "mp4")

    @unittest.skip('disabling act/part parsing for now.')
    def test_parse_file_name_with_act_1(self):
        """
        Test parsing a name with an 'act'.
        """
        name = parse_file_name('EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.act.1.XXX.2160p.mp4')
        self.assertEqual(name.site, "EvilAngel")
        self.assertEqual(name.date, "2022-01-03")
        self.assertEqual(name.name, "Carmela Clutch Fabulous Anal 3-Way")
        self.assertEqual(name.trans, False)
        self.assertEqual(name.act, "act 1")
        self.assertEqual(name.extension, "mp4")

    @unittest.skip('disabling act/part parsing for now.')
    def test_parse_file_name_with_part_1(self):
        """
        Test parsing a name with an 'part'.
        """

        name = parse_file_name('EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.part-1.720p.mp4')
        self.assertEqual(name.site, "EvilAngel")
        self.assertEqual(name.date, "2022-01-03")
        self.assertEqual(name.name, "Carmela Clutch Fabulous Anal 3-Way")
        self.assertEqual(name.act, "part-1")
        self.assertEqual(name.trans, False)
        self.assertEqual(name.extension, "mp4")

    @unittest.skip('disabling act/part parsing for now.')
    def test_parse_file_name_with_xxx_segment_after_part(self):
        """
        Test parsing a name with garbage after the 'part'
        """
        name = parse_file_name('EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.part-1-XXX.mp4')
        self.assertEqual(name.site, "EvilAngel")
        self.assertEqual(name.date, "2022-01-03")
        self.assertEqual(name.name, "Carmela Clutch Fabulous Anal 3-Way")
        self.assertEqual(name.act, "part-1")
        self.assertEqual(name.trans, False)
        self.assertEqual(name.extension, "mp4")

    def test_parse_file_name_with_trans(self):
        """
        Test parsing a name with a TS tag after the date, uncommon, but not unheard of.
        """
        name = parse_file_name('EvilAngel.22.01.03.TS.Carmela.Clutch.Fabulous.Anal.3-Way.part-1-XXX.mp4')
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
        name = parse_file_name('Twistys Feature Film.16.04.07.aidra.fox.the.getaway.part.1.mp4')
        self.assertEqual(name.site, "TwistysFeatureFilm")
        self.assertEqual(name.date, "2016-04-07")
        self.assertEqual(name.name, "aidra fox the getaway part 1")
        self.assertEqual(name.act, None)
        self.assertEqual(name.trans, False)
        self.assertEqual(name.extension, "mp4")

if __name__ == '__main__':
    unittest.main()
