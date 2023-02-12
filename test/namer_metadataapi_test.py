"""
Test namer_metadataapi_test.py
"""
import io
import unittest
from unittest import mock

from namer.comparison_results import SceneType
from namer.fileinfo import parse_file_name
from namer.command import make_command
from namer.metadataapi import main, match
from test.utils import environment, sample_config


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    def test_parse_response_metadataapi_net_dorcel(self):
        """
        Test parsing a stored response as a LookedUpFileInfo
        """
        with environment() as (_path, _parrot, config):
            name = parse_file_name("DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.mp4", sample_config())
            results = match(name, config)
            self.assertEqual(len(results.results), 1)
            result = results.results[0]
            info = result.looked_up
            self.assertEqual(info.name, "Peeping Tom")
            self.assertEqual(info.date, "2021-12-23")
            self.assertEqual(info.site, "Dorcel Club")
            self.assertIsNotNone(info.description)
            if info.description is not None:
                self.assertRegex(info.description, r"kissing in a parking lot")
            self.assertEqual(
                info.source_url, "https://dorcelclub.com/en/scene/85289/peeping-tom"
            )
            self.assertIn(
                "bg-dorcel-club-peeping-tom",
                info.poster_url if info.poster_url else "",
            )
            self.assertEqual(info.performers[0].name, "Ryan Benetti")
            self.assertEqual(info.performers[1].name, "Aya Benetti")
            self.assertEqual(info.performers[2].name, "Bella Tina")
            self.assertEqual(info.performers[3].name, "Megane Lopez")
            self.assertEqual(info.new_file_name("{network}", config), "")

    def test_parse_response_metadataapi_net_dorcel_unicode_cruft(self):
        """
        Test parsing a stored response as a LookedUpFileInfo
        """
        with environment() as (_path, _parrot, config):
            # the "e"s in the string below are unicode е (0x435), not asci e (0x65).
            name = parse_file_name("DorcеlClub - 2021-12-23 - Aya.Bеnеtti.Mеgane.Lopеz.And.Bеlla.Tina.mp4", sample_config())
            results = match(name, config)
            self.assertEqual(len(results.results), 1)
            result = results.results[0]
            self.assertTrue(result.is_match())
            info = result.looked_up
            self.assertEqual(info.name, "Peeping Tom")
            self.assertEqual(info.date, "2021-12-23")
            self.assertEqual(info.site, "Dorcel Club")
            self.assertIsNotNone(info.description)
            if info.description is not None:
                self.assertRegex(info.description, r"kissing in a parking lot")
            self.assertEqual(
                info.source_url, "https://dorcelclub.com/en/scene/85289/peeping-tom"
            )
            self.assertIn(
                "bg-dorcel-club-peeping-tom.",
                info.poster_url if info.poster_url else "",
            )
            self.assertEqual(info.performers[0].name, "Ryan Benetti")
            self.assertEqual(info.performers[1].name, "Aya Benetti")
            self.assertEqual(info.performers[2].name, "Bella Tina")
            self.assertEqual(info.performers[3].name, "Megane Lopez")

    def test_call_metadataapi_net(self):
        """
        Test parsing a stored response as a LookedUpFileInfo
        """
        with environment() as (_path, _parrot, config):
            name = parse_file_name("EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4", sample_config())
            results = match(name, config)
            self.assertEqual(len(results.results), 1)
            result = results.results[0]
            self.assertTrue(result.date_match)
            self.assertTrue(result.site_match)
            self.assertGreaterEqual(result.name_match, 90.0)
            info = results.results[0].looked_up
            self.assertEqual(info.name, "Carmela Clutch: Fabulous Anal 3-Way!")
            self.assertEqual(info.date, "2022-01-03")
            self.assertEqual(info.site, "Evil Angel")
            self.assertEqual(info.network, "Gamma Enterprises")
            self.assertIsNotNone(info.description)
            if info.description is not None:
                self.assertRegex(
                    info.description, r"brunette Carmela Clutch positions her big, juicy"
                )
            self.assertEqual(
                info.source_url,
                "https://evilangel.com/en/video/Carmela-Clutch-Fabulous-Anal-3-Way/198543",
            )
            self.assertIn(
                "bg-evil-angel-carmela-clutch-fabulous-anal-3-way",
                info.poster_url if info.poster_url else ""
            )
            self.assertEqual(info.performers[0].name, "Carmela Clutch")
            self.assertEqual(info.performers[0].role, "Female")
            self.assertEqual(info.performers[1].name, "Francesca Le")
            self.assertEqual(info.performers[1].role, "Female")
            self.assertEqual(info.performers[2].name, "Mark Wood")
            self.assertEqual(info.performers[2].role, "Male")
            self.assertEqual(info.new_file_name("{name}", config), "Carmela Clutch Fabulous Anal 3-Way!")
            self.assertEqual(info.new_file_name("{year}", config), "2022")
            self.assertEqual(info.new_file_name("{network}", config), "GammaEnterprises")

    def test_call_metadataapi_net2(self):
        """
        Test parsing a stored response as a LookedUpFileInfo
        """
        config = sample_config()
        config.min_file_size = 0
        with environment(config) as (_path, _parrot, config):
            name = parse_file_name("BrazzersExxtra.22.02.28.Marykate.Moss.Suck.Suck.Blow.XXX.1080p.MP4-WRB-xpost.mp4", sample_config())
            results = match(name, config)
            self.assertEqual(len(results.results), 1)
            result = results.results[0]
            self.assertTrue(result.date_match)
            self.assertTrue(result.site_match)
            self.assertGreaterEqual(result.name_match, 90.0)
            info = results.results[0].looked_up
            self.assertEqual(info.name, "Suck, Suck, Blow")
            self.assertEqual(info.date, "2022-02-28")
            self.assertEqual(info.site, "Brazzers Exxtra")

    def test_call_full_metadataapi_net(self):
        """
        Test parsing a full stored response (with tags) as a LookedUpFileInfo
        """
        with environment() as (_path, _parrot, config):
            name = parse_file_name("EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4", sample_config())
            results = match(name, config)
            self.assertEqual(len(results.results), 1)
            result = results.results[0]
            self.assertTrue(result.date_match)
            self.assertTrue(result.site_match)
            self.assertGreaterEqual(result.name_match, 90.0)
            info = results.results[0].looked_up
            self.assertEqual(info.name, "Carmela Clutch: Fabulous Anal 3-Way!")
            self.assertEqual(info.date, "2022-01-03")
            self.assertEqual(info.site, "Evil Angel")
            self.assertEqual(info.external_id, "198543")
            self.assertEqual(info.type, SceneType.SCENE)
            self.assertIsNotNone(info.description)
            if info.description is not None:
                self.assertRegex(info.description, r"brunette Carmela Clutch positions her big, juicy")
            self.assertEqual(info.source_url, "https://evilangel.com/en/video/Carmela-Clutch-Fabulous-Anal-3-Way/198543")
            self.assertIsNotNone(info.poster_url)
            if info.poster_url is not None:
                self.assertRegex(info.poster_url, "bg-evil-angel-carmela-clutch-fabulous-anal-3-way")
            self.assertEqual(info.performers[0].name, "Carmela Clutch")
            self.assertEqual(info.performers[0].role, "Female")
            self.assertEqual(info.performers[1].name, "Francesca Le")
            self.assertEqual(info.performers[1].role, "Female")
            self.assertEqual(info.performers[2].name, "Mark Wood")
            self.assertEqual(info.performers[2].role, "Male")

    def test_call_metadataapi_net_no_data(self):
        """
        verify an empty response from porndb is properly handled.
        """
        with environment() as (tempdir, _parrot, config):
            filename: str = 'GoodAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4'
            with open((tempdir / filename), 'w'):
                pass
            command = make_command((tempdir / filename), config)
            self.assertIsNotNone(command)
            if command is not None:
                results = match(command.parsed_file, config)
                self.assertEqual(len(results.results), 0)

    def test_call_metadataapi_net_no_message(self):
        """
        failed response (empty) is properly handled
        """
        config = sample_config()
        config.min_file_size = 0
        with environment() as (tempdir, _parrot, config):
            filename: str = 'OkAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4'
            with open((tempdir / filename), 'w'):
                pass
            command = make_command((tempdir / filename), config)
            self.assertIsNotNone(command)
            if command is not None:
                results = match(command.parsed_file, config)
                self.assertEqual(len(results.results), 0)

    @mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_main_metadataapi_net(self, mock_stdout):
        """
        Test parsing a full stored response (with tags) as a LookedUpFileInfo
        """
        with environment() as (tempdir, _parrot, config):
            filename: str = 'EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4'
            tmp_file = tempdir / filename
            with open(tmp_file, 'w'):
                pass
            main(["-f", str(tmp_file), "-c", str(config.config_file)])
            self.assertIn("Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! [WEBDL-].mp4", mock_stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
