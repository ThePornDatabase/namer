from posixpath import dirname
import unittest
from unittest.mock import patch, DEFAULT
import os
import tempfile
from distutils.dir_util import copy_tree
from namer_file_parser import parse_file_name
from namer_metadataapi_test import readfile
from namer import main
from mutagen.mp4 import MP4

def_rootdir = './test/'

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
        copy_tree(os.path.join(current, test_fixture), test_root)
        return tmpdir

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_writing_metadata_file(self, mock_poster, mock_response) :
        # Setup
        tmpdir = UnitTestAsTheDefaultExecution.prepare_workdir()
        path = os.path.join(tmpdir.name,'test',"DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.json")
        print("path"+path)
        response  = readfile(path)
        mock_response.return_value = response
        mock_poster.return_value = os.path.join(tmpdir.name,'test',"poster.png")
        input = os.path.join(tmpdir.name, 'test', "Site.22.01.01.painful.pun.XXX.720p.xpost.mp4")
        targetfile = os.path.join(tmpdir.name, 'test', "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p.mp4")
        os.rename(input, targetfile)

        main(['-f',targetfile])
  
        print("file" + os.path.join(os.path.dirname(targetfile), 'DorcelClub - 2021-12-23 - Peeping Tom.mp4'))
      
        output = MP4(os.path.join(os.path.dirname(targetfile), 'DorcelClub - 2021-12-23 - Peeping Tom.mp4'))
        self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])
        tmpdir.cleanup()

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_writing_metadata_dir(self, mock_poster, mock_response) :
        # Setup
        tmpdir = UnitTestAsTheDefaultExecution.prepare_workdir()
        path = os.path.join(tmpdir.name,'test',"DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.json")
        print("path"+path)
        response  = readfile(path)
        mock_response.return_value = response
        input = os.path.join(tmpdir.name, 'test')
        targetfile = os.path.join(tmpdir.name, "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p")
        os.rename(input, targetfile)
        mock_poster.return_value = os.path.join(targetfile,"poster.png")

        main(['-d',targetfile])

        output = MP4(os.path.join(tmpdir.name, "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p",'DorcelClub - 2021-12-23 - Peeping Tom.mp4'))
        self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])
        tmpdir.cleanup()

    @patch('namer_metadataapi.__get_response_json_object')
    @patch('namer.get_poster')
    def test_writing_metadata_all_dirs(self, mock_poster, mock_response) :
        # Setup
        tmpdir = UnitTestAsTheDefaultExecution.prepare_workdir()
        path = os.path.join(tmpdir.name,'test',"DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.json")
        print("path"+path)
        response  = readfile(path)
        mock_response.return_value = response
        input = os.path.join(tmpdir.name, 'test')
        targetfile = os.path.join(tmpdir.name, "DorcelClub - 2021-12-23 - Aya.Benetti.Megane.Lopez.And.Bella.Tina.XXX.1080p")
        os.rename(input, targetfile)
        copy_tree(targetfile, targetfile+"2")
        mock_poster.return_value = os.path.join(targetfile,"poster.png")
        main(['-d',os.path.dirname(targetfile),'-m'])
        output = MP4(os.path.join(targetfile, 'DorcelClub - 2021-12-23 - Peeping Tom.mp4'))
        self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])
        output = MP4(os.path.join(targetfile+"2", 'DorcelClub - 2021-12-23 - Peeping Tom.mp4'))
        self.assertEqual(output.get('\xa9nam'), ['Peeping Tom'])
        tmpdir.cleanup()

if __name__ == '__main__':
    unittest.main()         