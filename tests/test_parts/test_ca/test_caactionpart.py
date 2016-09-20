import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, ANY

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# module imports
from malcolm.core.vmetas import NumberMeta
from malcolm.parts.ca.caactionpart import CAActionPart, catools



class caint(int):
    ok = True


class TestCAPart(unittest.TestCase):

    def create_part(self, params=None):
        if params is None:
            params = dict(
                name="mname",
                description="desc",
                pv="pv",
            )

        params = CAActionPart.MethodMeta.prepare_input_map(params)
        p = CAActionPart(MagicMock(), params)
        p.set_logger_name("something")
        self.yielded = list(p.create_methods())
        return p

    def test_init(self):
        p = self.create_part()
        self.assertEqual(p.params.pv, "pv")
        self.assertEqual(p.params.value, 1)
        self.assertEqual(p.params.wait, True)
        self.assertEqual(p.method.description, "desc")
        self.assertEqual(self.yielded, [("mname", ANY, p.caput)])

    def test_reset(self):
        catools.caget.reset_mock()
        p = self.create_part()
        catools.caget.return_value = [caint(4)]
        p.connect_pvs("unused task object")
        catools.caget.assert_called_with(["pv"])

    def test_caput(self):
        catools.caput.reset_mock()
        p = self.create_part()
        p.caput()
        catools.caput.assert_called_once_with(
            "pv", 1, wait=True, timeout=None)

    def test_caput_status_pv_ok(self):
        catools.caput.reset_mock()
        p = self.create_part(dict(
            name="mname", description="desc", pv="pv", status_pv="spv",
            good_status="All Good"))
        catools.caget.return_value = "All Good"
        p.caput()

    def test_caput_status_pv_no_good(self):
        catools.caput.reset_mock()
        p = self.create_part(dict(
            name="mname", description="desc", pv="pv", status_pv="spv",
            good_status="All Good"))
        catools.caget.return_value = "No Good"
        self.assertRaises(AssertionError, p.caput)


if __name__ == "__main__":
    unittest.main(verbosity=2)
