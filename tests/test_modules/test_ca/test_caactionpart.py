import unittest
from mock import patch, ANY

from malcolm.core import call_with_params
from malcolm.modules.ca.parts import CAActionPart


class caint(int):
    ok = True
    

@patch("malcolm.modules.ca.parts.caactionpart.CaToolsHelper")
class TestCAActionPart(unittest.TestCase):

    def create_part(self, params=None):
        if params is None:
            params = dict(
                name="mname",
                description="desc",
                pv="pv",
            )

        p = call_with_params(CAActionPart, **params)
        self.yielded = list(p.create_methods())
        return p

    def test_init(self, catools):
        p = self.create_part()
        self.assertEqual(p.params.pv, "pv")
        self.assertEqual(p.params.value, 1)
        self.assertEqual(p.params.wait, True)
        self.assertEqual(p.method.description, "desc")
        self.assertEqual(self.yielded, [("mname", ANY, p.caput)])

    def test_reset(self, catools):
        p = self.create_part()
        p.catools.caget.reset_mock()
        p.catools.caget.return_value = [caint(4)]
        p.connect_pvs("unused context object")
        p.catools.caget.assert_called_with(["pv"])

    def test_caput(self, catools):
        p = self.create_part()
        p.catools.caput.reset_mock()
        p.caput()
        p.catools.caput.assert_called_once_with(
            "pv", 1, wait=True, timeout=None)

    def test_caput_status_pv_ok(self, catools):
        p = self.create_part(dict(
            name="mname", description="desc", pv="pv", statusPv="spv",
            goodStatus="All Good"))
        p.catools.caput.reset_mock()
        p.catools.caget.return_value = "All Good"
        p.caput()

    def test_caput_status_pv_no_good(self, catools):
        p = self.create_part(dict(
            name="mname", description="desc", pv="pv", statusPv="spv",
            goodStatus="All Good"))
        catools.caput.reset_mock()
        catools.caget.return_value = "No Good"
        self.assertRaises(AssertionError, p.caput)
