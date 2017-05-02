import unittest
from mock import MagicMock, patch

from malcolm.core import call_with_params, AlarmSeverity, AlarmStatus
from malcolm.modules.builtin.vmetas import NumberMeta
from malcolm.modules.ca.parts.capart import CAPart


class caint(int):
    ok = True
    severity = 0
    raw_stamp = (340000, 43)


@patch("malcolm.modules.ca.parts.capart.CaToolsHelper")
class TestCAPart(unittest.TestCase):

    def create_part(self, params=None):
        if params is None:
            params = dict(
                name="attrname",
                description="desc",
                pv="pv",
                rbvSuff="2"
            )

        class MyCAPart(CAPart):
            create_meta = MagicMock(return_value=NumberMeta("int32"))
            get_datatype = MagicMock()

        p = call_with_params(MyCAPart, **params)
        list(p.create_attributes())
        return p

    def test_init(self, catools):
        p = self.create_part()
        assert p.params.pv == "pv"
        assert p.params.rbv == "pv2"
        assert p.attr.meta == p.create_meta.return_value

    def test_init_no_pv_no_rbv(self, catools):
        # create test for no pv or rbv
        params = dict(name="", description="")
        with self.assertRaises(ValueError):
            self.create_part(params)

    def test_init_with_rbv(self, catools):
        params = dict(name="", description="", pv="pv", rbv="rbv")
        p = self.create_part(params)
        assert p.params.rbv == "rbv"
        assert p.params.pv == "pv"

    def test_init_no_rbv(self, catools):
        params = dict(name="", description="", pv="pv")
        p = self.create_part(params)
        assert p.params.rbv == "pv"
        assert p.params.pv == "pv"

    def test_reset(self, catools):
        p = self.create_part()
        p.catools.caget.return_value = [caint(4), caint(5)]
        p.reset("unused context object")
        p.catools.caget.assert_called_with(
            ["pv2", "pv"],
            format=p.catools.FORMAT_CTRL, datatype=p.get_datatype())
        p.catools.camonitor.assert_called_once_with(
            "pv2", p.monitor_callback, format=p.catools.FORMAT_TIME,
            datatype=p.get_datatype(), notify_disconnect=True)
        assert p.attr.value == 4
        assert p.monitor == p.catools.camonitor()

    def test_caput(self, catools):
        p = self.create_part()
        p.catools.caput.reset_mock()
        p.catools.caget.reset_mock()
        p.catools.caget.return_value = caint(3)
        p.caput(32)
        datatype = p.get_datatype.return_value
        p.catools.caput.assert_called_once_with(
            "pv", 32, wait=True, timeout=None, datatype=datatype)
        p.catools.caget.assert_called_once_with(
            "pv2", format=p.catools.FORMAT_TIME, datatype=datatype)
        assert p.attr.value == 3

    def test_close_monitor(self, catools):
        p = self.create_part()
        m = MagicMock()
        p.monitor = m
        p.close_monitor()
        m.close.assert_called_once_with()
        assert p.monitor == None

    def test_update_value_good(self, catools):
        p = self.create_part()
        value = caint(4)
        p.update_value(value)
        assert p.attr.value == 4
        assert p.attr.timeStamp.secondsPastEpoch == 340000
        assert p.attr.timeStamp.nanoseconds == 43
        assert p.attr.timeStamp.userTag == 0
        assert p.attr.alarm.severity == AlarmSeverity.NO_ALARM
        assert p.attr.alarm.status == AlarmStatus.NO_STATUS
        assert p.attr.alarm.message == ""

    def test_update_value_bad(self, catools):
        p = self.create_part()
        value = caint(44)
        value.ok = False
        p.update_value(value)
        assert p.attr.value == 0
        assert p.attr.alarm.severity == AlarmSeverity.INVALID_ALARM
        assert p.attr.alarm.status == AlarmStatus.DEVICE_STATUS
        assert p.attr.alarm.message == "PV disconnected"
