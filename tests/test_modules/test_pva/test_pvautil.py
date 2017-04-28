import unittest
from mock import patch, MagicMock
from collections import OrderedDict
import sys

import numpy as np

# Mock out pvaccess if it isn't there
if "pvaccess" not in sys.modules:
    sys.modules["pvaccess"] = MagicMock()
import pvaccess

from malcolm.core import StringArray
from malcolm.modules.pva.controllers.pvautil import pva_structure_from_value, \
    dict_to_pv_object


class PvTempObject(object):
    def __init__(self, dict_in, type):
        self._dict = dict_in
        self._type = type

    def __repr__(self):
        s = "<PvTempObject type=%s dict=%s>"%(self._type, str(self._dict))
        return s

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            for key in self._dict:
                if key in other._dict:
                    if self._dict[key] != other._dict[key]:
                        return False
                else:
                    return False
            return self._type == other._type
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def set(self, dict_in):
        self._dict = dict_in


class TestPVAUtil(unittest.TestCase):

    @patch("malcolm.modules.pva.controllers.pvautil.pvaccess.PvObject", PvTempObject)
    def test_dict_to_stucture(self):
        val_dict = OrderedDict()
        val_dict["typeid"] = "type1"
        val_dict["val1"] = "1"
        val_dict["val2"] = np.int32(2)
        val_dict["val3"] = True
        val_dict["val4"] = np.int64(0)
        val_dict["val5"] = np.float64(0.5)
        val_dict["val6"] = StringArray('', '')
        val_dict["val7"] = np.array([5, 1], dtype=np.int32)
        val_dict["val8"] = [True, False]
        val_dict["val9"] = np.array([0, 1], dtype=np.int64)
        val_dict["val10"] = np.array([0.2, 0.6], dtype=np.float64)
        val = pva_structure_from_value(val_dict)
        test_dict = OrderedDict()
        test_dict["val1"] = pvaccess.STRING
        test_dict["val2"] = pvaccess.INT
        test_dict["val3"] = pvaccess.BOOLEAN
        test_dict["val4"] = pvaccess.LONG
        test_dict["val5"] = pvaccess.DOUBLE
        test_dict["val6"] = [pvaccess.STRING]
        test_dict["val7"] = [pvaccess.INT]
        test_dict["val8"] = [pvaccess.BOOLEAN]
        test_dict["val9"] = [pvaccess.LONG]
        test_dict["val10"] = [pvaccess.DOUBLE]
        test_val = PvTempObject(test_dict, "type1")
        self.assertEquals(val, test_val)

        # Test the variant union array type
        val = pva_structure_from_value(
            {"union_array": [
                {"val1": 1},
                {"val2": "2"}
            ]})
        test_dict = OrderedDict()
        test_dict["union_array"] = [()]
        test_val = PvTempObject(test_dict, "")
        self.assertEquals(val, test_val)
        val = pva_structure_from_value(
            {"union_array": []})
        test_dict = OrderedDict()
        test_dict["union_array"] = [()]
        test_val = PvTempObject(test_dict, "")
        self.assertEquals(val, test_val)

    @patch("malcolm.modules.pva.controllers.pvautil.pvaccess.PvObject", PvTempObject)
    def test_dict_to_pv(self):
        val_dict = OrderedDict()
        val_dict["typeid"] = "type1"
        val_dict["val1"] = StringArray('', '')
        val_dict["val2"] = np.array((1, 2))
        val_dict["val3"] = dict(a=43)
        val_dict["val4"] = [True, False]
        val_dict["val5"] = [dict(a=43), dict(b=44)]
        val_dict["val6"] = "s"
        actual = dict_to_pv_object(val_dict)
        self.assertEqual(actual._type, "type1")
        self.assertEqual(actual._dict["val1"], ["", ""])
        self.assertEqual(actual._dict["val2"], [1, 2])
        self.assertEqual(actual._dict["val3"], dict(a=43))
        self.assertEqual(actual._dict["val4"], [True, False])
        self.assertEqual(len(actual._dict["val5"]), 2)
        self.assertEqual(actual._dict["val5"][0]._dict, dict(a=43))
        self.assertEqual(actual._dict["val5"][1]._dict, dict(b=44))
        self.assertEqual(actual._dict["val6"], "s")




if __name__ == "__main__":
    unittest.main(verbosity=2)
