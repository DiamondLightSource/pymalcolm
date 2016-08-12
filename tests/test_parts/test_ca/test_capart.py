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
from malcolm.parts.ca.capart import CAPart, capart_takes, catools


class caint(int):
    ok = True


class TestCAPart(unittest.TestCase):

    def create_part(self, params=None):
        if params is None:
            params = dict(
                name="attrname",
                description="desc",
                pv="pv",
                rbv_suff="2"
            )

        @capart_takes()
        class MyCAPart(CAPart):
            create_meta = MagicMock(return_value=NumberMeta("int32"))
            get_datatype = MagicMock()

        params = MyCAPart.MethodMeta.prepare_input_map(params)

        p = MyCAPart(MagicMock(), params)
        p.set_logger_name("something")
        list(p.create_attributes())
        return p

    def test_init(self):
        p = self.create_part()
        self.assertEqual(p.params.pv, "pv")
        self.assertEqual(p.params.rbv, "pv2")
        self.assertEqual(p.attr.meta, p.create_meta.return_value)

    def test_init_no_pv_no_rbv(self):
        # create test for no pv or rbv
        params = dict(name="", description="")
        self.assertRaises(ValueError, self.create_part, params)

    def test_init_no_rbv(self):
        params = dict(name="", description="", pv="pv", rbv="rbv")
        p = self.create_part(params)
        self.assertEqual(p.params.rbv, "rbv")
        self.assertEqual(p.params.pv, "pv")

    def test_init_no_rbv(self):
        params = dict(name="", description="", pv="pv")
        p = self.create_part(params)
        self.assertEqual(p.params.rbv, "pv")
        self.assertEqual(p.params.pv, "pv")

    def test_reset(self):
        p = self.create_part()
        catools.caget.return_value = [caint(4), caint(5)]
        p.connect_pvs("unused task object")
        catools.caget.assert_called_with(
            ["pv2", "pv"],
            format=catools.FORMAT_CTRL, datatype=p.get_datatype())
        catools.camonitor.assert_called_once_with(
            "pv2", p.on_update, format=catools.FORMAT_CTRL,
            datatype=p.get_datatype(), notify_disconnect=True)
        self.assertEqual(p.attr.value, 4)
        self.assertEqual(p.monitor, catools.camonitor())

    def test_caput(self):
        catools.caput.reset_mock()
        catools.caget.reset_mock()
        catools.caget.return_value = caint(3)
        p = self.create_part()
        p.caput(32)
        datatype = p.get_datatype.return_value
        catools.caput.assert_called_once_with(
            "pv", 32, wait=True, timeout=None, datatype=datatype)
        catools.caget.assert_called_once_with(
            "pv2", format=catools.FORMAT_CTRL, datatype=datatype)
        self.assertEqual(p.attr.value, 3)

    def test_monitor_update(self):
        p = self.create_part()
        p.on_update("value")
        p.process.spawn.assert_called_once_with(p.update_value, "value")

    def test_close_monitor(self):
        p = self.create_part()
        m = MagicMock()
        p.monitor = m
        p.close_monitor()
        m.close.assert_called_once_with()
        self.assertEqual(p.monitor, None)

    def test_update_value_good(self):
        p = self.create_part()
        value = caint(4)
        p.update_value(value)
        self.assertEqual(p.attr.value, 4)

    def test_update_value_bad(self):
        p = self.create_part()
        value = caint(44)
        value.ok = False
        p.update_value(value)
        self.assertEqual(p.attr.value, None)

if __name__ == "__main__":
    unittest.main(verbosity=2)
