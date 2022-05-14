"""
Testing utils
"""
import os
import platform
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List

from mutagen.mp4 import MP4

from namer.types import default_config, NamerConfig


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
            "Anal",
            "Ass",
            "Ass to mouth",
            "Big Dick",
            "Blowjob",
            "Blowjob - Double",
            "Brunette",
            "Bubble Butt",
            "Cum swallow",
            "Deepthroat",
            "FaceSitting",
            "Facial",
            "Gonzo / No Story",
            "HD Porn",
            "Hairy Pussy",
            "Handjob",
            "Hardcore",
            "Latina",
            "MILF",
            "Pussy to mouth",
            "Rimming",
            "Sex",
            "Tattoo",
            "Threesome",
            "Toys / Dildos",
        ],
        output2.get("keyw"),
    )


@dataclass(init=True, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class ProcessingTarget:
    """
    Test data.
    """

    file: Path
    json_search: str
    json_exact: str
    poster: Path
    expect_match: bool


def new_ea(targetdir: Path, use_dir: bool = True, post_stem: str = "", match: bool = True):
    """
    Creates a test mp4 in a temp directory, with a name to match the returned contents of ./test/ea.json
    optionally, names the dir and not the mp4 file to match.
    optionally, inserts a string between the file stem and suffix.
    optionally, will ensure a match doesn't occure.
    """
    current = Path(__file__).resolve().parent
    test_mp4 = current / "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4"
    search_json_file = current / "ea.json"
    exact_json_file = current / "ea.full.json"
    test_poster = current / "poster.png"
    name = "EvilAngel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way!" + post_stem
    target_file = targetdir / (name + ".mp4")
    if use_dir is True:
        target_file = targetdir / name / "qwerty.mp4"
    os.makedirs(target_file.parent, exist_ok=True)
    target_file.parent.chmod(int("700", base=8))
    shutil.copy(test_mp4, target_file)
    test_mp4.chmod(int("600", base=8))
    poster = Path(tempfile.mktemp(suffix=".png"))
    shutil.copy(test_poster, poster)
    return ProcessingTarget(target_file, search_json_file.read_text(), exact_json_file.read_text(), poster, match)


def prepare(targets: List[ProcessingTarget], mock_poster, mock_response):
    """
    Prepares mocks for responses based on targets input.
    """
    targets.sort(key=lambda x: str(x.file))
    posters = []
    responses = []
    for target in targets:
        posters.append(target.poster)
        if target.expect_match is True:
            responses.append(target.json_search)
            responses.append(target.json_exact)
        else:
            responses.append("{}")
            responses.append("{}")
            responses.append("{}")
            responses.append("{}")
            responses.append("{}")
            responses.append("{}")
            responses.append("{}")
            responses.append("{}")
    mock_poster.side_effect = posters
    mock_response.side_effect = responses


def sample_config() -> NamerConfig:
    """
    Attempts reading various locations to fine a namer.cfg file.
    """
    os.environ["NAMER_CONFIG"] = "./namer.cfg.sample"
    return default_config()
