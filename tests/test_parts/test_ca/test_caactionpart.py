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
from malcolm.core import Process, SyncFactory
from malcolm.parts.ca.caactionpart import CAActionPart



class caint(int):
    ok = True


class TestCAActionPart(unittest.TestCase):

    def setUp(self):
        sf = SyncFactory("sf")
        self.process = Process("process", sf)

    def tearDown(self):
        del self.process.sync_factory

    def create_part(self, params=None):
        if params is None:
            params = dict(
                name="mname",
                description="desc",
                pv="pv",
            )

        params = CAActionPart.MethodMeta.prepare_input_map(**params)
        p = CAActionPart(self.process, params)
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
        p = self.create_part()
        p.catools.caget.reset_mock()
        p.catools.caget.return_value = [caint(4)]
        p.connect_pvs("unused task object")
        p.catools.caget.assert_called_with(["pv"])

    def test_caput(self):
        p = self.create_part()
        p.catools.caput.reset_mock()
        p.caput()
        p.catools.caput.assert_called_once_with(
            "pv", 1, wait=True, timeout=None)

    def test_caput_status_pv_ok(self):
        p = self.create_part(dict(
            name="mname", description="desc", pv="pv", statusPv="spv",
            goodStatus="All Good"))
        p.catools.caput.reset_mock()
        p.catools.caget.return_value = "All Good"
        p.caput()

    def test_caput_status_pv_no_good(self):
        p = self.create_part(dict(
            name="mname", description="desc", pv="pv", statusPv="spv",
            goodStatus="All Good"))
        p.catools.caput.reset_mock()
        p.catools.caget.return_value = "No Good"
        self.assertRaises(AssertionError, p.caput)


if __name__ == "__main__":
    unittest.main(verbosity=2)
