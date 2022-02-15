"""
Test of namer_dirscanner.py
"""
from pathlib import Path
import unittest
from distutils.dir_util import copy_tree
import tempfile
from namer_dirscanner import find_largest_file_in_glob, find_targets_for_naming


def prepare_workdir(tmpdir: str) -> Path:
    """
    Each tests get's it's own resources to work on in a temporary file.
    This copies the "./test" dir in to that temp dir.
    """
    tempdir = Path(tmpdir)
    target = tempdir / "test"
    current = Path(__file__).resolve().parent
    copy_tree(current / "test" , str(target))
    return tmpdir


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    current = Path(__file__).resolve().parent

    def test_find_largest_file_in_glob(self):
        """
        Testing find_largest_file_in_glob happy path
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            tempdir = Path(tmpdir)
            subdir = tempdir / "subdir"
            subdir.mkdir()
            sub_sub_dir = tempdir / "subdir" / "subdir"
            sub_sub_dir.mkdir()
            file = subdir / "file.txt"
            file.write_text("small file")
            bigger_file = sub_sub_dir / "bigger_file.txt"
            bigger_file.write_text("a bigger file")
            found_file = find_largest_file_in_glob(subdir, "**/*.txt")
            self.assertEqual(str(found_file), str(bigger_file))

    def test_to_process(self):
        """
        Testing find_targets_for_naming happy path.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            prepare_workdir(tmpdir)
            targetdir = Path(tmpdir) / "test"
            to_process = find_targets_for_naming(targetdir)
            self.assertEqual(Path(to_process[0][1]).name, 'Site.22.01.01.painful.pun.XXX.720p.xpost.mp4')


if __name__ == '__main__':
    unittest.main()
