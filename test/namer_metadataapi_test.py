"""
Test namer_metadataapi_test.py
"""
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from namer.filenameparts import parse_file_name
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
            name = parse_file_name("DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.mp4")
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
                "/unsafe/1000x1500/smart/filters:sharpen():upscale():watermark(https%3A%2F%2Fcdn.metadataapi.net%2Fsites%2F15%2Fe1%2Fac%2Fe028ae39fdc24d6d0fed4ecf14e53ae%2Flogo%2Fdorcelclub-logo.png,-10,-10,25)/https%3A%2F%2Fcdn.metadataapi.net%2Fscene%2F6e%2Fca%2F89%2F05343d45d85ef2d480ed63f6311d229%2Fbackground%2Fbg-dorcel-club-peeping-tom.jpg",
                info.poster_url if info.poster_url else "",
            )
            self.assertEqual(info.performers[0].name, "Ryan Benetti")
            self.assertEqual(info.performers[1].name, "Aya Benetti")
            self.assertEqual(info.performers[2].name, "Bella Tina")
            self.assertEqual(info.performers[3].name, "Megane Lopez")

    def test_parse_response_metadataapi_net_dorcel_unicode_cruft(self):
        """
        Test parsing a stored response as a LookedUpFileInfo
        """
        with environment() as (_path, _parrot, config):
            # the "e"s in the string below are unicode е (0x435), not asci e (0x65).
            name = parse_file_name("DorcеlClub - 2021-12-23 - Aya.Bеnеtti.Mеgane.Lopеz.And.Bеlla.Tina.mp4")
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
                "/unsafe/1000x1500/smart/filters:sharpen():upscale():watermark(https%3A%2F%2Fcdn.metadataapi.net%2Fsites%2F15%2Fe1%2Fac%2Fe028ae39fdc24d6d0fed4ecf14e53ae%2Flogo%2Fdorcelclub-logo.png,-10,-10,25)/https%3A%2F%2Fcdn.metadataapi.net%2Fscene%2F6e%2Fca%2F89%2F05343d45d85ef2d480ed63f6311d229%2Fbackground%2Fbg-dorcel-club-peeping-tom.jpg",
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
            name = parse_file_name("EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4")
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
                "/unsafe/1000x1500/smart/filters:sharpen():upscale()/https%3A%2F%2Fcdn.metadataapi.net%2Fscene%2F01%2F92%2F04%2F76e780fd19c4306bc744f79b5cb4bce%2Fbackground%2Fbg-evil-angel-carmela-clutch-fabulous-anal-3-way.jpg",
                info.poster_url if info.poster_url else ""
            )
            self.assertEqual(info.performers[0].name, "Carmela Clutch")
            self.assertEqual(info.performers[0].role, "Female")
            self.assertEqual(info.performers[1].name, "Francesca Le")
            self.assertEqual(info.performers[1].role, "Female")
            self.assertEqual(info.performers[2].name, "Mark Wood")
            self.assertEqual(info.performers[2].role, "Male")
            self.assertEqual(info.new_file_name(template="{name}"), "Carmela Clutch Fabulous Anal 3-Way!")

    @mock.patch("namer.metadataapi.__get_response_json_object")
    def test_call_metadataapi_net2(self, mock_response):
        """
        Test parsing a stored response as a LookedUpFileInfo
        """
        response = Path(__file__).resolve().parent / "ssb2.json"
        mock_response.return_value = response.read_text()
        name = parse_file_name("BrazzersExxtra.22.02.28.Marykate.Moss.Suck.Suck.Blow.XXX.1080p.MP4-WRB-xpost.mp4")
        results = match(name, sample_config())
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
            name = parse_file_name("EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4")
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
            self.assertIsNotNone(info.description)
            if info.description is not None:
                self.assertRegex(info.description, r"brunette Carmela Clutch positions her big, juicy")
            self.assertEqual(info.source_url, "https://evilangel.com/en/video/Carmela-Clutch-Fabulous-Anal-3-Way/198543")
            self.assertIsNotNone(info.poster_url)
            if info.poster_url is not None:
                self.assertRegex(info.poster_url, "http.*/unsafe/1000x1500/smart/.*%2Fbackground%2Fbg-evil-angel-carmela-clutch-fabulous-anal-3-way.jpg")
            self.assertEqual(info.performers[0].name, "Carmela Clutch")
            self.assertEqual(info.performers[0].role, "Female")
            self.assertEqual(info.performers[1].name, "Francesca Le")
            self.assertEqual(info.performers[1].role, "Female")
            self.assertEqual(info.performers[2].name, "Mark Wood")
            self.assertEqual(info.performers[2].role, "Male")

    @mock.patch("namer.metadataapi.__get_response_json_object")
    def test_call_metadataapi_net_no_data(self, mock_response):
        """
        verify an empty response from porndb is properly handled.
        """
        config = sample_config()
        config.min_file_size = 0
        mock_response.return_value = "{}"
        filename: str = 'EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4'
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            with open((tempdir / filename), 'w'):
                pass
            command = make_command((tempdir / filename), config)
            self.assertIsNotNone(command)
            if command is not None:
                results = match(command.parsed_file, config)
                self.assertEqual(len(results.results), 0)

    @mock.patch("namer.metadataapi.__get_response_json_object")
    def test_call_metadataapi_net_no_message(self, mock_response):
        """
        failed response (empty) is properly handled
        """
        config = sample_config()
        config.min_file_size = 0
        mock_response.return_value = ""
        filename: str = 'EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4'
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            with open((tempdir / filename), 'w'):
                pass
            command = make_command((tempdir / filename), config)
            self.assertIsNotNone(command)
            if command is not None:
                results = match(command.parsed_file, config)
                self.assertEqual(len(results.results), 0)

    @mock.patch("namer.metadataapi.__get_response_json_object")
    def test_call_metadataapi_net_none_message(self, mock_response):
        """
        failed response (None) is properly handled
        """
        config = sample_config()
        config.min_file_size = 0
        mock_response.return_value = None
        filename: str = 'EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4'
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            with open((tempdir / filename), 'w'):
                pass
            command = make_command((tempdir / filename), config)
            self.assertIsNotNone(command)
            if command is not None:
                results = match(command.parsed_file, config)
                self.assertEqual(len(results.results), 0)

    @mock.patch("sys.stdout", new_callable=io.StringIO)
    @mock.patch("namer.metadataapi.default_config")
    def test_main_metadataapi_net(self, mock_config, mock_stdout):
        """
        Test parsing a full stored response (with tags) as a LookedUpFileInfo
        """
        with environment() as (tempdir, _parrot, config):
            config.min_file_size = 0
            mock_config.side_effect = [config]
            filename: str = 'EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.mp4'
            tmp_file = tempdir / filename
            with open(tmp_file, 'w'):
                pass
            main(["-f", str(tmp_file)])
            self.assertIn("EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!.mp4", mock_stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
