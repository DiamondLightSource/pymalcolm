import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

from malcolm.parts.ca.cadoublepart import CADoublePart

import unittest
from mock import Mock, patch, ANY


class TestCADoublePart(unittest.TestCase):

    def test_init(self):
            CADoublePart.create_attribute = Mock()
            # reading yaml will result in a dictionary such as:-
            exposure_pv={"name": "exposure",
                         "description": "shutter time",
                         "pv": "BL00I-EA-DET-01:AcquireTime",
                         "rbv_suff": "_RBV"}
            p = CADoublePart("exp", Mock(), Mock(), exposure_pv)

            # TODO: add above exposure_pv params
            p.create_attribute.assert_called_once_with(ANY,
                    "BL00I-EA-DET-01:AcquireTime", rbv=None, rbv_suff='_RBV')

