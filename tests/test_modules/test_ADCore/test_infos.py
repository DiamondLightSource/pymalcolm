import unittest

from malcolm.modules.ADCore.infos import FilePathTranslatorInfo


class TestInfo(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_file_path_translator_drive_mount(self):
        info = FilePathTranslatorInfo("C", "/foo")
        part_info = {"WINPATH": [info]}
        win_path = info.translate_filepath(part_info, "/foo/directory")

        assert "C:\\directory" == win_path

    def test_file_path_translator_network_mount(self):
        info = FilePathTranslatorInfo("", "/foo")
        part_info = {"WINPATH": [info]}
        win_path = info.translate_filepath(part_info, "/foo/directory")

        assert "\\\\dc\\foo\\directory" == win_path

    def test_file_path_translator_network_science(self):
        info = FilePathTranslatorInfo("", "/foo", "//science")
        part_info = {"WINPATH": [info]}
        win_path = info.translate_filepath(part_info, "/foo/directory")

        assert "\\\\science\\foo\\directory" == win_path
