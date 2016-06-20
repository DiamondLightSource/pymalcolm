import os
import sys
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths

from mock import MagicMock, patch
from scanpointgenerator import Generator

from malcolm.core.pointgeneratormeta import PointGeneratorMeta


class TestPointGeneratorMeta(unittest.TestCase):

    def setUp(self):
        self.PGM = PointGeneratorMeta("test_name", "test_description")

    def test_init(self):
        self.assertEqual("test_name", self.PGM.name)
        self.assertEqual("test_description", self.PGM.description)

    def test_validate(self):
        g = Generator()

        self.PGM.validate(g)

    def test_validate_raises(self):
        with self.assertRaises(TypeError):
            self.PGM.validate(7)

    def test_to_dict(self):
        expected_dict = OrderedDict()
        expected_dict["description"] = "test_description"
        expected_dict["metaOf"] = "malcolm:core/PointGenerator:1.0"

        response = self.PGM.to_dict()

        self.assertEqual(expected_dict, response)

    def test_from_dict(self):
        _dict = OrderedDict()
        _dict["description"] = "test_description"
        _dict["metaOf"] = "malcolm:core/PointGenerator:1.0"

        response = self.PGM.from_dict("test_name", _dict)

        self.assertEqual(response.name, "test_name")
        self.assertEqual(response.description, "test_description")
        self.assertEqual(response.metaOf, "malcolm:core/PointGenerator:1.0")

if __name__ == "__main__":
    unittest.main(verbosity=2)
