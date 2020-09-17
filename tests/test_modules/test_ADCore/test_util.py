import unittest

from malcolm.modules.ADCore.util import make_xml_filename


class TestMakeXmlFilename(unittest.TestCase):
    def test_make_xml_filename_returns_path_for_default_suffix(self):
        file_dir = "/file/dir"
        mri = "TEST_MRI"

        expected_filename = "/file/dir/TEST_MRI-attributes.xml"
        actual_filename = make_xml_filename(file_dir, mri)

        self.assertEqual(expected_filename, actual_filename)

    def test_make_xml_filename_returns_path_for_custom_suffix(self):
        file_dir = "/file/dir"
        mri = "TEST_MRI"
        suffix = "layout"

        expected_filename = "/file/dir/TEST_MRI-layout.xml"
        actual_filename = make_xml_filename(file_dir, mri, suffix=suffix)

        self.assertEqual(expected_filename, actual_filename)

    def test_make_xml_filename_converts_colons_in_mri_to_underscore(self):
        file_dir = "/file/dir"
        mri = "TEST:MRI:NAME"

        expected_filename = "/file/dir/TEST_MRI_NAME-attributes.xml"
        actual_filename = make_xml_filename(file_dir, mri)

        self.assertEqual(expected_filename, actual_filename)
