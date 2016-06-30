import os
import sys
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths

from mock import MagicMock, patch

from malcolm.core.pointgeneratormeta import PointGeneratorMeta, CompoundGenerator


class TestPointGeneratorMeta(unittest.TestCase):

    def setUp(self):
        self.PGM = PointGeneratorMeta("test_name", "test_description")

    def test_init(self):
        self.assertEqual("test_name", self.PGM.name)
        self.assertEqual("test_description", self.PGM.description)

    def test_validate(self):
        g = CompoundGenerator([MagicMock()], [])

        self.PGM.validate(g)

    @patch('malcolm.core.pointgeneratormeta.CompoundGenerator.from_dict')
    def test_validate_dict_then_create_and_return(self, from_dict_mock):
        gen_mock = MagicMock()
        from_dict_mock.return_value = gen_mock
        d = dict()

        response = self.PGM.validate(d)

        from_dict_mock.assert_called_once_with(d)
        self.assertEqual(gen_mock, response)

    def test_validate_raises(self):
        with self.assertRaises(TypeError):
            self.PGM.validate(7)

    def test_to_dict(self):
        expected_dict = OrderedDict()
        expected_dict["typeid"] = "malcolm:core/PointGeneratorMeta:1.0"
        expected_dict["description"] = "test_description"
        expected_dict["tags"] = []
        expected_dict["writeable"] = True

        response = self.PGM.to_dict()

        self.assertEqual(expected_dict, response)

    def test_from_dict(self):
        _dict = OrderedDict()
        _dict["description"] = "test_description"
        _dict["typeid"] = "malcolm:core/PointGeneratorMeta:1.0"
        _dict["tags"] = ["tag"]
        _dict["writeable"] = False

        response = self.PGM.from_dict("test_name", _dict)

        self.assertEqual(response.name, "test_name")
        self.assertEqual(response.description, "test_description")
        self.assertEqual(
            response.typeid, "malcolm:core/PointGeneratorMeta:1.0")
        self.assertEqual(response.tags, ["tag"])
        self.assertEqual(response.writeable, False)

if __name__ == "__main__":
    unittest.main(verbosity=2)
