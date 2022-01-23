import unittest
from namer_file_parser import parse_file_name

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
        self.assertEqual(name.trans, False)
        self.assertEqual(name.extension, "mp4")

    def test_parse_file_name_with_act_1(self):
        name = parse_file_name('EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.act.1.XXX.2160p.mp4')
        self.assertEqual(name.site, "EvilAngel")
        self.assertEqual(name.date, "2022-01-03")
        self.assertEqual(name.name, "Carmela Clutch Fabulous Anal 3-Way")
        self.assertEqual(name.trans, False)
        self.assertEqual(name.act, "act 1")
        self.assertEqual(name.extension, "mp4")

    def test_parse_file_name_with_part_1(self):
        name = parse_file_name('EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.part-1.720p.mp4')
        self.assertEqual(name.site, "EvilAngel")
        self.assertEqual(name.date, "2022-01-03")
        self.assertEqual(name.name, "Carmela Clutch Fabulous Anal 3-Way")
        self.assertEqual(name.act, "part-1")
        self.assertEqual(name.trans, False)
        self.assertEqual(name.extension, "mp4")

    def test_parse_file_name_with_part1(self):
        name = parse_file_name('EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.part-1-XXX.mp4')
        self.assertEqual(name.site, "EvilAngel")
        self.assertEqual(name.date, "2022-01-03")
        self.assertEqual(name.name, "Carmela Clutch Fabulous Anal 3-Way")
        self.assertEqual(name.act, "part-1")
        self.assertEqual(name.trans, False)
        self.assertEqual(name.extension, "mp4") 

    def test_parse_file_name_with_trans(self):
        name = parse_file_name('EvilAngel.22.01.03.TS.Carmela.Clutch.Fabulous.Anal.3-Way.part-1-XXX.mp4')
        self.assertEqual(name.site, "EvilAngel")
        self.assertEqual(name.date, "2022-01-03")
        self.assertEqual(name.name, "Carmela Clutch Fabulous Anal 3-Way")
        self.assertEqual(name.act, "part-1")
        self.assertEqual(name.trans, True)
        self.assertEqual(name.extension, "mp4") 

if __name__ == '__main__':
    unittest.main()
