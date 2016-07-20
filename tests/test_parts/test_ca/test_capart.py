import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock
from cothread import catools

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# module imports
from malcolm.core.block import DummyLock
from malcolm.parts.ca.capart import CAPart

class TestCAPart(unittest.TestCase):

    def create_part(self, params=None):
        if params is None:
            params =  dict(meta=MagicMock(), pv="pv", rbv_suff="2")
            params["meta"].name = "meta"

        process = MagicMock()
        block = MagicMock()

        class MyCAPart(CAPart):
            def _call_setup(self, anything):
                self.create_attribute(**params)

        p = MyCAPart("me", process, block, "anything")
        return p

    def test_init(self):
        p = self.create_part()
        self.assertEqual(p.rbv, "pv2")
        p.block.add_attribute.assert_called_once_with(p.attr)

    def test_init_no_rbv(self):
        params = dict(meta=MagicMock(), pv="pv")
        params["meta"].name = "meta"
        p = self.create_part(params)
        self.assertEqual(p.rbv, "pv")
        self.assertEqual(p.pv, "pv")

    def test_reset(self):
        p = self.create_part()
        catools.connect.return_value = MagicMock(ok=True)
        p.connect_pvs()
        catools.connect.assert_called_with(["pv", "pv2"], cainfo=True)
        catools.camonitor.assert_called_once_with(
            "pv2", on_update=p.on_update, format=catools.FORMAT_TIME,
            datatype=None, notify_disconnect=True)
        self.assertEqual(p.monitor, catools.camonitor())

    def test_caput(self):
        class caint(int):
            ok = True
        catools.caget.return_value = caint(3)
        p = self.create_part()
        p.attr.put(32)
        catools.caput.assert_called_once_with(
            "pv", 32, wait=True, timeout=None)
        catools.caget.assert_called_once_with(
            "pv2")
        p.meta.validate.assert_called_once_with(catools.caget.return_value)
        self.assertEqual(p.attr.value, p.meta.validate())

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

    def test_get_datatype(self):
        p = self.create_part()
        p.long_string = True
        self.assertEqual(p.get_datatype(), catools.DBR_CHAR_STR)

    def test_update_value_good(self):
        p = self.create_part()
        p.block.lock = DummyLock()
        value = MagicMock(ok=True)
        p.update_value(value)
        p.meta.validate.assert_called_once_with(value)
        self.assertEqual(p.attr.value, p.meta.validate())

    def test_update_value_bad(self):
        p = self.create_part()
        p.block.lock = DummyLock()
        value = MagicMock(ok=False)
        p.update_value(value)
        p.block.state.set_value.assert_called_once_with(
            "Fault", notify=False)
        p.block.status.set_value.assert_called_once_with(
            "CA disconnect on %s" % value.name, notify=False)
        p.block.busy.set_value.assert_called_once_with(False)

if __name__ == "__main__":
    unittest.main(verbosity=2)
