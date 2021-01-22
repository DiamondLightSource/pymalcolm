import unittest

from malcolm.modules.ADCore.infos import FilePathTranslatorInfo, NDAttributeDatasetInfo


class TestInfo(unittest.TestCase):
    def test_file_path_translator_drive_mount_succeeds_with_valid_path(self):
        info = FilePathTranslatorInfo("C", "/foo", "")
        part_info = {"WINPATH": [info]}
        win_path = info.translate_filepath(part_info, "/foo/directory/file_name.xml")

        assert "C:\\directory\\file_name.xml" == win_path

    def test_file_path_translator_network_mount_succeeds_with_valid_path(self):
        info = FilePathTranslatorInfo("", "/foo", "//dc")
        part_info = {"WINPATH": [info]}
        win_path = info.translate_filepath(part_info, "/foo/directory")

        assert "\\\\dc\\foo\\directory" == win_path

    def test_file_path_translator_raises_AssertionError_with_bad_filepath_prefix(self):
        info = FilePathTranslatorInfo("C", "/foo", "")
        part_info = {"WINPATH": [info]}
        filepath = "foo/directory"

        self.assertRaises(AssertionError, info.translate_filepath, part_info, filepath)

    def test_file_path_translator_raises_AssertionError_with_colon_in_filepath(self):
        info = FilePathTranslatorInfo("C", "/foo", "")
        part_info = {"WINPATH": [info]}
        filepath = "/foo/directory/bad:filename"

        self.assertRaises(AssertionError, info.translate_filepath, part_info, filepath)


class TestNDAttributeDatasetInfo(unittest.TestCase):
    def test_from_attribute_type_raises_AttributeError_with_bad_dataset_type(self):

        self.assertRaises(
            AttributeError,
            NDAttributeDatasetInfo.from_attribute_type,
            "POSITION",
            float,
            "POSITION.X",
        )
