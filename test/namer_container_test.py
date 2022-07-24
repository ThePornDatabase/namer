#
#   Config
#
#   FileParser
#
#

from pathlib import Path
import shutil
from unittest import TestCase
import unittest

from namer.filenameparser import parse_file_name
from namer.ffmpeg import ffprobe
from namer.name_formatter import PartialFormatter
from namer.configuration import NamerConfig
from namer.configuration_utils import default_config, configure_logging_verifier

from test.utils import environment, sample_config

from dependency_injector import containers, providers

class Services(containers.DeclarativeContainer):

    # Namer's external configuration - perhaps redundant or highly coupled, or both
    namer_configuration = providers.Singleton(
        default_config
    )

    # The formatter that can convert FileNameParts to a full name
    name_formatter = providers.Singleton(
        PartialFormatter
    )

    properly_configured = providers.Singleton(
        configure_logging_verifier,
        configuration=namer_configuration,
        formatter=name_formatter,
    )


class WorkItem(containers.DeclarativeContainer):

    config = providers.Configuration()

    services = providers.Container(
        Services,
    )

    target_file = providers.Singleton(
        str,
        config.get("file")
    )

    target_path = providers.Singleton(
        Path,
        target_file
    )

    ffprobe_results = providers.Singleton(
        ffprobe,
        target_path
    )

    file_name_parts = providers.Singleton(
        parse_file_name,
        filename=target_file,
        # TODO: regex_config=services.namer_configuration.name_parser
    )


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """
    def test_get_resolution(self):
        with environment() as (tempdir, _parrot, config):
            container = Services()
            container.namer_configuration.override(providers.Object(config))
            for provider in container.traverse():
                print(provider)
            print(container)

            container.load_config()
            container.check_dependencies()
            container.init_resources()
            
            self.assertTrue(container.properly_configured())
            item_container = WorkItem()



            test_dir = Path(__file__).resolve().parent
            target_file = (tempdir / "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.mp4")
            shutil.copy(test_dir / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4", target_file)
            poster = tempdir / "poster.png"

            
            item_container = WorkItem()
            item_container.assign_parent(container)
            item_container.target_file.override(providers.Object(str(target_file)))
            ffprobe_results = item_container.ffprobe_results()
            file_name_parts = item_container.file_name_parts()
            self.assertIsNotNone(ffprobe_results)
            self.assertIsNotNone(file_name_parts)
            
           
            #self.assertEqual(len(results), 1)
            #result = results[0]
            #info = result.looked_up
            #self.assertEqual(info.name, "Peeping Tom")
            #self.assertEqual(info.date, "2021-12-23")
            #self.assertEqual(info.site, "Dorcel Club")
            #self.assertIsNotNone(info.description)
            #if info.description is not None:
            #    self.assertRegex(info.description, r"kissing in a parking lot")
            #self.assertEqual(
            #    info.source_url, "https://dorcelclub.com/en/scene/85289/peeping-tom"
            #)
            #self.assertIn(
            #    "/unsafe/1000x1500/smart/filters:sharpen():upscale():watermark(https%3A%2F%2Fcdn.metadataapi.net%2Fsites%2F15%2Fe1%2Fac%2Fe028ae39fdc24d6d0fed4ecf14e53ae%2Flogo%2Fdorcelclub-logo.png,-10,-10,25)/https%3A%2F%2Fcdn.metadataapi.net%2Fscene%2F6e%2Fca%2F89%2F05343d45d85ef2d480ed63f6311d229%2Fbackground%2Fbg-dorcel-club-peeping-tom.jpg",
            #    info.poster_url if info.poster_url else "",
            #)
            #self.assertEqual(info.performers[0].name, "Ryan Benetti")
            #self.assertEqual(info.performers[1].name, "Aya Benetti")
            #self.assertEqual(info.performers[2].name, "Bella Tina")
            #self.assertEqual(info.performers[3].name, "Megane Lopez")


        print("okay")
        #container.config.set(file)