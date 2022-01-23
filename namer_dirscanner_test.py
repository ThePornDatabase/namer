import unittest
import os
from distutils.dir_util import copy_tree
import tempfile
from namer_dirscanner import find_largest_file_in_glob, find_targets_for_naming


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    current=os.path.dirname(os.path.abspath(__file__))

    def prepare_workdir():
        current=os.path.dirname(os.path.abspath(__file__))
        test_fixture="test"
        tmpdir = tempfile.TemporaryDirectory()
        test_root = os.path.join(tmpdir.name,test_fixture)
        copy_tree(os.path.join(current, test_fixture), tmpdir.name)
        return tmpdir


    def test_find_largest_file_in_glob(self):
        tmpdir = UnitTestAsTheDefaultExecution.prepare_workdir()
        targetdir = os.path.join(tmpdir.name, "nzb_dir")
        file = find_largest_file_in_glob(targetdir, "**/*.txt")
        self.assertRegex(text=file, expected_regex="real_file/bigger_file.txt")
        tmpdir.cleanup()

    def test_to_process(self):
        tmpdir = UnitTestAsTheDefaultExecution.prepare_workdir()
        to_process = find_targets_for_naming(tmpdir.name)
        print("will process: {} ".format(to_process))
        self.assertEqual(os.path.basename(to_process[0][1]), 'Site.22.01.01.painful.pun.XXX.720p.xpost.mp4')

if __name__ == '__main__':
    unittest.main()      