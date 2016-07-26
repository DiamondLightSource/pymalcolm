import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

from cothread import catools
from malcolm.parts.ca.cachararraypart import CACharArrayPart

import unittest
from mock import Mock, patch, ANY


class TestCACharPart(unittest.TestCase):
    def test_init(self):
        CACharArrayPart.create_attribute = Mock()
        # reading yaml will result in a dictionary such as:-
        d = {"name": "pv",
             "description": "a test pv",
             "pv": "Prefix:Suffix",
             "rbv_suff": "_RBV"}
        p = CACharArrayPart("part", Mock(), Mock(), d)

        p.create_attribute.assert_called_once_with(ANY,
                                                   "Prefix:Suffix", rbv=None,
                                                   rbv_suff='_RBV')
        self.assertEqual(p.get_datatype(), catools.DBR_CHAR_STR)

if __name__ == "__main__":
    unittest.main(verbosity=2)