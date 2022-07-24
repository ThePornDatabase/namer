from pathlib import Path
import shutil
import unittest

from namer.filenameparts import parse_file_name
from namer.ffmpeg import ffprobe
from namer.name_formatter import PartialFormatter
from namer.configuration_utils import default_config, configure_logging_verifier

from test.utils import environment

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

            item_container = WorkItem()
            item_container.assign_parent(container)
            item_container.target_file.override(providers.Object(str(target_file)))
            ffprobe_results = item_container.ffprobe_results()
            file_name_parts = item_container.file_name_parts()
            self.assertIsNotNone(ffprobe_results)
            self.assertIsNotNone(file_name_parts)

        print("okay")
