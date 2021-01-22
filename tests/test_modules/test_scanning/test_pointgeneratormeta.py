import unittest

from mock import MagicMock, patch
from scanpointgenerator import CompoundGenerator

from malcolm.modules.scanning.util import PointGeneratorMeta


class TestPointGeneratorMeta(unittest.TestCase):
    def setUp(self):
        self.PGM = PointGeneratorMeta("test_description")

    def test_init(self):
        assert "test_description" == self.PGM.description
        assert self.PGM.label == ""

    def test_validate(self):
        g = CompoundGenerator([], [], [])
        self.PGM.validate(g)

    @patch("malcolm.modules.scanning.util.CompoundGenerator.from_dict")
    def test_validate_dict_then_create_and_return(self, from_dict_mock):
        gen_mock = MagicMock()
        from_dict_mock.return_value = gen_mock
        d = dict()
        response = self.PGM.validate(d)
        from_dict_mock.assert_called_once_with(d)
        assert gen_mock == response

    def test_validate_raises(self):
        with self.assertRaises(TypeError):
            self.PGM.validate(7)
