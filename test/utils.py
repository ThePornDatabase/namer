"""
Testing utils
"""
import contextlib
import json
import os
import platform
import shutil
import tempfile
from configupdater import ConfigUpdater
from dataclasses import dataclass
from importlib import resources

from pathlib import Path
from sys import gettrace as sys_gettrace
from time import sleep, time
from typing import Any, Callable, Dict, Optional

from mutagen.mp4 import MP4

from namer.configuration import NamerConfig
from namer.configuration_utils import to_ini, from_config
from test.web.parrot_webserver import ParrotWebServer


def is_debugging():
    return sys_gettrace() is not None


class Wait:
    _predicate: Optional[Callable[[], bool]] = None
    _duration: int = 10
    _checking: float = 0.1

    def __init__(self):
        pass

    def seconds(self, seconds: int) -> 'Wait':
        self._duration = seconds
        return self

    def checking(self, seconds: float) -> 'Wait':
        self._checking = seconds
        return self

    def until(self, func: Callable[[], bool]) -> 'Wait':
        self._predicate = func
        return self

    def __wait(self, state: bool):
        max_time: float = time() + float(self._duration)
        while time() < max_time or is_debugging():
            if not self._predicate:
                raise RuntimeError("you must set a predicate to wait on before calling attempting to wait.")
            predicate = self._predicate
            if predicate and predicate() == state:
                return
            sleep(self._checking)
        raise RuntimeError(f"Timed out waiting for predicate {self._predicate} to return {state}")

    def isTrue(self):
        self.__wait(True)

    def isFalse(self):
        self.__wait(False)


def sample_config() -> NamerConfig:
    """
    Attempts reading various locations to fine a namer.cfg file.
    """
    config = ConfigUpdater()
    config_str = ""
    if hasattr(resources, 'files'):
        config_str = resources.files("namer").joinpath("namer.cfg.default").read_text()
    elif hasattr(resources, 'read_text'):
        config_str = resources.read_text("namer", "namer.cfg.default")
    config.read_string(config_str)
    namer_config = from_config(config, NamerConfig())
    namer_config.extra_sleep_time = 0
    namer_config.config_updater = config
    return namer_config


class FakeTPDB(ParrotWebServer):

    _scenes: Dict[str, Any] = {}

    def __init__(self):
        super().__init__()
        self._scenes: dict[str, Any] = {
            "ea.full.json": self.get_localized_json_in_file("ea.full.json"),
            "dc.json": self.get_localized_json_in_file("dc.json"),
            "ssb2.json": self.get_localized_json_in_file("ssb2.json"),
        }

        self.default_additions()

    def __enter__(self):
        super().__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return super().__exit__(exc_type, exc_value, traceback)

    def get_url(self) -> str:
        return super().get_url()

    def add_json_response(self, response, target_url: str):
        return_value = response
        return_value = json.dumps(json.loads(return_value), separators=(',', ':'))
        modified_value = return_value.replace(r'https://thumb.metadataapi.net/', super().get_url())
        super().set_response(target_url, modified_value)

    def get_localized_json_in_file(self, jsonfile):
        test_dir = Path(__file__).resolve().parent
        return_value = (test_dir / jsonfile).read_text()
        return_value = json.dumps(json.loads(return_value), separators=(',', ':'))
        modified_value = return_value.replace(r'https://thumb.metadataapi.net/', super().get_url())
        usable_json = json.loads(modified_value)
        return usable_json

    def add_json_response_file(self, jsonfile, target_url: str):
        usable_json = self.get_localized_json_in_file(jsonfile)
        super().set_response(target_url, json.dumps(usable_json, separators=(',', ':')))

    def get_json(self, _json_reponses: str) -> str:
        return json.dumps(self._scenes[_json_reponses], separators=(',', ':'))

    def add_evil_angel(self, target_url: str):
        super().set_response(target_url, lambda: self.get_json("ea.full.json"))

    def add_dorcel_club(self, target_url: str):
        super().set_response(target_url, lambda: self.get_json("dc.json"))

    def add_brazzers_extra(self, target_url: str):
        super().set_response(target_url, lambda: self.get_json("ssb2.json"))

    def add_poster(self, target_url: str) -> None:
        test_dir = Path(__file__).resolve().parent
        return_value = (test_dir / "poster.png").read_bytes()
        super().set_response(target_url, bytearray(return_value))

    def default_additions(self):

        # Evil Angel:
        # Search Results
        self.add_evil_angel("/scenes?parse=evilangel.2022-01-03.Carmela%20Clutch%20Fabulous%20Anal%203-Way&limit=25")
        self.add_evil_angel("/scenes?parse=evilangel.2022-01-03.Carmela%20Clutch%20Fabulous%20Anal%203-Way%21&limit=25")
        self.add_evil_angel("/scenes?parse=evilangel.2022-01-03.Carmela%20Clutch%20Fabulous%20Anal%203-Way%212&limit=25")
        self.add_evil_angel("/scenes?parse=evilangel.2022-01-03.Carmela%20Clutch%20Fabulous%20Anal%203-Way%211&limit=25")
        self.add_evil_angel("/scenes?parse=evilangel.Carmela%20Clutch%20Fabulous%20Anal%203-Way&limit=25")
        self.add_evil_angel("/scenes?parse=evilangel.Carmela%20Clutch%20Fabulous%20Anal%203-Way%21&limit=25")
        self.add_evil_angel("/scenes?parse=evilangel.2022-01-03.&limit=25")
        # Extra Metadata Lookup
        self.add_evil_angel("/scenes/1678283?")

        self.add_evil_angel("/movies?parse=evilangel.2022-01-03.Carmela%20Clutch%20Fabulous%20Anal%203-Way&limit=25")
        self.add_evil_angel("/movies?parse=evilangel.Carmela%20Clutch%20Fabulous%20Anal%203-Way&limit=25")
        self.add_evil_angel("/movies?parse=evilangel.2022-01-03.&limit=25")
        self.add_evil_angel("/movies/1678283?")

        self.add_evil_angel("/movies?parse=EvilAngel%20-%202022-01-03%20-%20Carmela%20Clutch%20Fabulous%20Anal%203-Way%21&limit=25")

        self.add_evil_angel("/scenes?parse=evilangel.2022-01-03.Carmela%20Clutch%20Fabulous%20Anal%203-Way%21number2&limit=25")

        # UI Tests
        self.add_evil_angel("/scenes?parse=EvilAngel%20-%202022-01-03%20-%20Carmela%20Clutch%20Fabulous%20Anal%203-Way%21&limit=25")
        self.add_evil_angel("/movies?parse=EvilAngel%20-%202022-01-03%20-%20Carmela%20Clutch%20Fabulous%20Anal%203-Way%21&limit=25")
        # Image for UI Test:
        self.add_evil_angel("/scenes?parse=EvilAngel.-.2022-01-03.-.Carmela.Clutch.Fabulous.Anal.3-Way%21.mp4&limit=25")
        self.add_poster("/qWAUIAUpBsoqKUwozc4NOTR1tPI=/1000x1500/smart/filters:sharpen():upscale():watermark(https://cdn.metadataapi.net/sites/3f/9f/51/cf3828d65425bca2890d53ef242d8cf/logo/evil-angel_dark[1].png,-10,-10,25,50)/https://cdn.metadataapi.net/scene/f4/ab/3e/a91d31d6dee223f4f30a57bfd83b151/background/bg-evil-angel-carmela-clutch-fabulous-anal-3-way.webp?")
        # DorcelClub
        # Search Results
        self.add_dorcel_club("/scenes?parse=dorcelclub.2021-12-23.Aya%20Benetti%20Megane%20Lopez%20And%20Bella%20Tina&limit=25")
        self.add_dorcel_club("/scenes?parse=dorcelclub.Aya%20Benetti%20Megane%20Lopez%20And%20Bella%20Tina&limit=25")
        self.add_dorcel_club("/scenes?parse=dorcelclub.2021-12-23.&limit=25")
        self.add_dorcel_club("/scenes?parse=dorcelclub.&limit=25")
        # Extra Metadata Lookup
        self.add_dorcel_club("/scenes/1674059?")
        # with utf8 characters
        self.add_dorcel_club("/scenes?parse=dorcelclub.2021-12-23.Aya%20B%D0%B5n%D0%B5tti%20M%D0%B5gane%20Lop%D0%B5z%20And%20B%D0%B5lla%20Tina&limit=25")

        # Brazzers Exxtra
        self.add_brazzers_extra("/scenes?parse=brazzersexxtra.2022-02-28.Marykate%20Moss%20Suck%20Suck%20Blow&limit=25")
        self.add_brazzers_extra("/scenes?parse=brazzersexxtra.Marykate%20Moss%20Suck%20Suck%20Blow&limit=25")
        self.add_brazzers_extra("/scenes?parse=brazzersexxtra.2022-02-28.&limit=25")
        self.add_brazzers_extra("/scenes?parse=brazzersexxtra.&limit=25")
        # Extra Metadata Lookup
        self.add_brazzers_extra("/scenes/1836175?")

        # None existant Good Angel:
        # Search Results
        self.add_json_response("{}", "/scenes?parse=goodangel.2022-01-03.Carmela%20Clutch%20Fabulous%20Anal%203-Way&limit=25")
        self.add_json_response("{}", "/scenes?parse=goodangel.Carmela%20Clutch%20Fabulous%20Anal%203-Way&limit=25")
        self.add_json_response("{}", "/scenes?parse=goodangel.2022-01-03.&limit=25")
        self.add_json_response("{}", "/scenes?parse=goodangel.&limit=25")
        self.add_json_response("{}", "/movies?parse=goodangel.2022-01-03.Carmela%20Clutch%20Fabulous%20Anal%203-Way&limit=25")
        self.add_json_response("{}", "/movies?parse=goodangel.Carmela%20Clutch%20Fabulous%20Anal%203-Way&limit=25")
        self.add_json_response("{}", "/movies?parse=goodangel.2022-01-03.&limit=25")
        self.add_json_response("{}", "/movies?parse=goodangel.&limit=25")

        self.add_json_response("""{
   "data" : {
      "favicon" : null,
      "id" : 1309,
      "logo" : null,
      "name" : "Gamma Enterprises",
      "network_id" : null,
      "parent_id" : null,
      "poster" : null,
      "short_name" : "gammaenterprises",
      "url" : "N/A"
   }
}""", "/sites/1309?")


@contextlib.contextmanager
def environment(config: NamerConfig = None):  # type: ignore
    if config is None:
        config = sample_config()

    with tempfile.TemporaryDirectory(prefix="test") as tmpdir, FakeTPDB() as fakeTpdb:
        tempdir = Path(tmpdir)

        config.override_tpdb_address = fakeTpdb.get_url()
        config.watch_dir = tempdir / "watch"
        config.watch_dir.mkdir(parents=True, exist_ok=True)
        config.dest_dir = tempdir / "dest"
        config.dest_dir.mkdir(parents=True, exist_ok=True)
        config.work_dir = tempdir / "work"
        config.work_dir.mkdir(parents=True, exist_ok=True)
        config.failed_dir = tempdir / "failed"
        config.failed_dir.mkdir(parents=True, exist_ok=True)
        config.porndb_token = "notarealtoken"
        cfgfile = tempdir / 'test_namer.cfg'
        config.min_file_size = 0
        with open(cfgfile, "w") as file:
            content = to_ini(config)
            file.write(content)
        config.config_file = cfgfile
        yield tempdir, fakeTpdb, config


def validate_permissions(test_self, file: Path, perm: int):
    """
    Validates file permissions are as expected.
    """
    if hasattr(os, "chmod") and platform.system() != "Windows":
        found = oct(file.stat().st_mode)[-3:]
        expected = str(perm)[-3:]
        print("Found {found}, Expected {expected}")
        # test_self.assertEqual(found, "664")
        test_self.assertEqual(found, expected)


def validate_mp4_tags(test_self, file):
    """
    Validates the tags of the standard mp4 file.
    """
    output2 = MP4(file)
    test_self.assertEqual(output2.get("\xa9nam"), ["Carmela Clutch: Fabulous Anal 3-Way!"])
    test_self.assertEqual(output2.get("\xa9day"), ["2022-01-03T09:00:00Z"])
    test_self.assertEqual(output2.get("\xa9alb"), ["Evil Angel"])  # plex collection
    test_self.assertEqual(output2.get("tvnn"), ["Evil Angel"])
    test_self.assertEqual(output2.get("\xa9gen"), ["Adult"])
    test_self.assertEqual(
        [
            'Anal',
            'Ass',
            'Atm',
            'Big Boobs',
            'Big Dick',
            'Blowjob',
            'Brunette',
            'Bubble Butt',
            'Cunnilingus',
            'Deepthroat',
            'Face Sitting',
            'Facial',
            'Fingering',
            'Hairy Pussy',
            'Handjob',
            'Hardcore',
            'Latina',
            'Milf',
            'Rimming',
            'Sex',
            'Swallow',
            'Threesome',
        ],
        output2.get("keyw"),
    )


@dataclass(init=True, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class ProcessingTarget:
    """
    Test data.
    """

    relative: Path
    file: Optional[Path]
    json_search: str
    json_exact: str
    poster: Path
    expect_match: bool
    source_file: str

    def setup(self, target_dir: Path):
        """
        Creates a test mp4 in a temp directory, with a name to match the returned contents of ./test/ea.json
        optionally, names the dir and not the mp4 file to match.
        optionally, inserts a string between the file stem and suffix.
        optionally, will ensure a match doesn't occur.
        """
        current = Path(__file__).resolve().parent
        test_mp4 = current / self.source_file
        self.file = target_dir / self.relative
        os.makedirs(self.file.parent, exist_ok=True)
        self.file.parent.chmod(0o700)
        with contextlib.suppress(Exception):
            shutil.copy(test_mp4, self.file)

        with contextlib.suppress(Exception):
            test_mp4.chmod(0o600)

    def get_file(self) -> Path:
        if self.file is None:
            raise RuntimeError("The ProcessingTarget has not had 'setup()' called, and hence file doesn't exist")
        return self.file


def new_ea(target_dir: Optional[Path] = None, relative: str = "", use_dir: bool = True, post_stem: str = "", match: bool = True, mp4_file_name: str = "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4"):
    """
    Creates a test mp4 in a temp directory, with a name to match the returned contents of ./test/ea.json
    optionally, names the dir and not the mp4 file to match.
    optionally, inserts a string between the file stem and suffix.
    optionally, will ensure a match doesn't occur.
    """
    name = relative + ("Evil" if match else "Ok") + "Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" + post_stem
    full_relative = Path(name) / (relative + "qwerty.mp4") if use_dir else Path(name + ".mp4")
    processing_target: ProcessingTarget = ProcessingTarget(full_relative, None, '', '', Path("/"), True, mp4_file_name)
    if target_dir:
        processing_target.setup(target_dir)
    return processing_target


def new_dorcel(target_dir: Optional[Path] = None, relative: str = "", use_dir: bool = True, post_stem: str = "", match: bool = True, mp4_file_name: str = "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4"):
    """
    Creates a test mp4 in a temp directory, with a name to match the returned contents of ./test/ea.json
    optionally, names the dir and not the mp4 file to match.
    optionally, inserts a string between the file stem and suffix.
    optionally, will ensure a match doesn't occur.
    """
    name = relative + ("Dorcel" if match else "Ok") + "Club - 2021-12-23 - Aya Benetti Megane Lopez Bella Tina" + post_stem
    full_relative = Path(name) / (relative + "qwerty.mp4") if use_dir else Path(name + ".mp4")
    processing_target: ProcessingTarget = ProcessingTarget(full_relative, None, '', '', Path("/"), True, mp4_file_name)
    if target_dir:
        processing_target.setup(target_dir)
    return processing_target
