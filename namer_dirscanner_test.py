"""
Test of namer_dirscanner.py
"""
import unittest
import os
from distutils.dir_util import copy_tree
import tempfile
from namer_dirscanner import find_largest_file_in_glob, find_targets_for_naming


def prepare_workdir(tmpdir: str) -> tempfile.TemporaryDirectory:
    """
    Each tests get's it's own resources to work on in a temporary file.
    This copies the "./test" dir in to that temp dir.
    """
    current = os.path.dirname(os.path.abspath(__file__))
    test_fixture = "test"
    copy_tree(os.path.join(current, test_fixture),
              os.path.join(tmpdir, "test"))
    return tmpdir


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    current = os.path.dirname(os.path.abspath(__file__))

    def test_find_largest_file_in_glob(self):
        """
        Testing find_largest_file_in_glob happy path
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            prepare_workdir(tmpdir)
            targetdir = os.path.join(tmpdir, "test", "nzb_dir")
            file = find_largest_file_in_glob(targetdir, "**/*.txt")
            self.assertRegex(text=file, expected_regex="real_file.*bigger_file.txt")

    def test_to_process(self):
        """
        Testing find_targets_for_naming happy path.
        """
        with tempfile.TemporaryDirectory(prefix="test") as tmpdir:
            prepare_workdir(tmpdir)
            to_process = find_targets_for_naming(os.path.join(tmpdir, "test"))
            self.assertEqual(os.path.basename(
                to_process[0][1]), 'Site.22.01.01.painful.pun.XXX.720p.xpost.mp4')


if __name__ == '__main__':
    unittest.main()
