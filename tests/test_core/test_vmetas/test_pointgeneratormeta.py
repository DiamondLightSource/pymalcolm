import os
import sys
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths

from mock import MagicMock, patch

from malcolm.core.vmetas import PointGeneratorMeta
from scanpointgenerator import CompoundGenerator


class TestPointGeneratorMeta(unittest.TestCase):

    def setUp(self):
        self.PGM = PointGeneratorMeta("test_description")

    def test_init(self):
        self.assertEqual("test_description", self.PGM.description)
        self.assertEqual(self.PGM.label, "")

    def test_validate(self):
        g = CompoundGenerator([MagicMock()], [], [])
        self.PGM.validate(g)

    @patch('malcolm.core.vmetas.pointgeneratormeta.CompoundGenerator.from_dict')
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

if __name__ == "__main__":
    unittest.main(verbosity=2)
