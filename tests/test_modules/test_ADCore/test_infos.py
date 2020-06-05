import unittest

from malcolm.modules.ADCore.infos import FilePathTranslatorInfo


class TestInfo(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_file_path_translator_drive_mount(self):
        info = FilePathTranslatorInfo("C", "/foo", "")
        part_info = {"WINPATH": [info]}
        win_path = info.translate_filepath(part_info, 
            "/foo/directory/file:name.xml")

        assert "C:\\directory\\file_name.xml" == win_path

    def test_file_path_translator_network_mount(self):
        info = FilePathTranslatorInfo("", "/foo", "//dc")
        part_info = {"WINPATH": [info]}
        win_path = info.translate_filepath(part_info, "/foo/directory")

        assert "\\\\dc\\foo\\directory" == win_path
