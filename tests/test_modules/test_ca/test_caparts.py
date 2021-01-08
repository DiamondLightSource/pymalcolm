import unittest

import numpy as np
from mock import ANY, patch

from malcolm.core import AlarmSeverity, Process, Table, Widget
from malcolm.modules.builtin.controllers import StatefulController


@patch("malcolm.modules.ca.util.catools")
class TestCAParts(unittest.TestCase):
    def setUp(self):
        self.process = Process("proc")
        self.process.start()

    def create_block(self, p, mri="mri"):
        c = StatefulController(mri)
        c.add_part(p)
        self.process.add_controller(c)
        b = self.process.block_view(mri)
        return b

    def tearDown(self):
        self.process.stop(timeout=2)

    def test_caboolean(self, catools):
        from malcolm.modules.ca.parts import CABooleanPart

        class Initial(int):
            ok = True
            severity = 0

        catools.caget.side_effect = [[Initial(0), Initial(0)]]
        b = self.create_block(
            CABooleanPart(name="attrname", description="desc", pv="pv", rbv_suffix="2")
        )
        assert b.attrname.value is False
        assert b.attrname.meta.description == "desc"
        assert b.attrname.meta.writeable
        catools.caget.assert_called_once_with(
            ["pv2", "pv"],
            datatype=catools.DBR_LONG,
            format=catools.FORMAT_CTRL,
            throw=True,
        )
        catools.caget.reset_mock()

        class Update(int):
            ok = True
            severity = 0
            raw_stamp = (34, 4355)

        catools.caget.side_effect = [Update(1)]
        b.attrname.put_value(True)
        catools.caput.assert_called_once_with(
            "pv", 1, datatype=catools.DBR_LONG, timeout=10.0, wait=True
        )
        catools.caget.assert_called_once_with(
            "pv2", datatype=catools.DBR_LONG, format=catools.FORMAT_TIME, throw=True
        )
        assert b.attrname.value is True
        assert b.attrname.alarm.is_ok()
        assert b.attrname.timeStamp.to_time() == 34.000004355

    def test_cachararray(self, catools):
        from malcolm.modules.ca.parts import CACharArrayPart

        class Initial(str):
            ok = True
            severity = 1

        catools.caget.side_effect = [[Initial("long_and_bad_string")]]
        b = self.create_block(
            CACharArrayPart(name="cattr", description="desc", rbv="pvr")
        )
        assert b.cattr.value == "long_and_bad_string"
        assert b.cattr.alarm.severity == AlarmSeverity.MINOR_ALARM
        catools.caget.assert_called_once_with(
            ["pvr"],
            datatype=catools.DBR_CHAR_STR,
            format=catools.FORMAT_CTRL,
            throw=True,
        )

    def test_cachoice(self, catools):
        from malcolm.modules.ca.parts import CAChoicePart

        class Initial(int):
            ok = True
            severity = 0
            enums = ["a", "b", "c"]

        catools.caget.side_effect = [[Initial(1), Initial(2)]]
        b = self.create_block(
            CAChoicePart(name="attrname", description="desc", pv="pv", rbv="rbv")
        )
        assert b.attrname.value == "b"
        assert b.attrname.meta.description == "desc"
        assert b.attrname.meta.writeable
        catools.caget.assert_called_once_with(
            ["rbv", "pv"],
            datatype=catools.DBR_ENUM,
            format=catools.FORMAT_CTRL,
            throw=True,
        )
        catools.caget.reset_mock()

        class Update(int):
            ok = True
            severity = 2
            raw_stamp = (34, 4355)

        catools.caget.side_effect = [Update(0)]
        b.attrname.put_value("c")
        catools.caput.assert_called_once_with(
            "pv", 2, datatype=catools.DBR_ENUM, timeout=10.0, wait=True
        )
        catools.caget.assert_called_once_with(
            "rbv", datatype=catools.DBR_ENUM, format=catools.FORMAT_TIME, throw=True
        )
        assert b.attrname.value == "a"
        assert b.attrname.alarm.severity == AlarmSeverity.MAJOR_ALARM
        assert b.attrname.timeStamp.to_time() == 34.000004355
        catools.caget.reset_mock()
        catools.caput.reset_mock()

        catools.caget.side_effect = [Update(1)]
        b.attrname.put_value(1)
        catools.caput.assert_called_once_with(
            "pv", 1, datatype=catools.DBR_ENUM, timeout=10.0, wait=True
        )
        assert b.attrname.value == "b"

    def test_cadoublearray(self, catools):
        from malcolm.modules.ca.parts import CADoubleArrayPart

        class Initial(np.ndarray):
            ok = True
            severity = 0
            precision = 5
            units = ""
            lower_disp_limit = -1.0
            upper_disp_limit = 10.0

        initial = Initial(dtype=np.float64, shape=(3,))
        initial[:] = np.arange(3) + 1.2

        catools.caget.side_effect = [[initial]]
        b = self.create_block(
            CADoubleArrayPart(name="attrname", description="desc", pv="pv", timeout=-1)
        )

        assert list(b.attrname.value) == [1.2, 2.2, 3.2]
        assert b.attrname.meta.description == "desc"
        assert b.attrname.meta.writeable
        assert b.attrname.meta.display.limitLow == -1.0
        assert b.attrname.meta.display.limitHigh == 10.0
        assert b.attrname.meta.display.precision == 5
        catools.caget.assert_called_once_with(
            ["pv"], datatype=catools.DBR_DOUBLE, format=catools.FORMAT_CTRL, throw=True
        )
        catools.caget.reset_mock()

        class Update(np.ndarray):
            ok = False

        catools.caget.side_effect = [Update(shape=(6,))]
        b.attrname.put_value([])
        catools.caput.assert_called_once_with(
            "pv", ANY, datatype=catools.DBR_DOUBLE, timeout=None, wait=True
        )
        assert list(catools.caput.call_args[0][1]) == []
        catools.caget.assert_called_once_with(
            "pv", datatype=catools.DBR_DOUBLE, format=catools.FORMAT_TIME, throw=True
        )
        assert list(b.attrname.value) == [1.2, 2.2, 3.2]
        assert b.attrname.alarm.severity == AlarmSeverity.UNDEFINED_ALARM

    def test_cawaveformtable(self, catools):
        from malcolm.modules.ca.parts import CAWaveformTablePart

        class Initial(np.ndarray):
            ok = True
            severity = 0
            precision = 7
            units = ""
            lower_disp_limit = 0.0
            upper_disp_limit = 0.0

        initialY = Initial(dtype=np.float64, shape=(3,))
        initialY.lower_disp_limit = np.e
        initialY.upper_disp_limit = 10.0
        initialY.name = "yPv"
        initialY[:] = np.arange(3) + 1.2
        initialX = Initial(dtype=np.float64, shape=(3,))
        initialX.upper_disp_limit = np.pi
        initialX.name = "xPv"
        initialX.units = "s"
        initialX[:] = (np.arange(3) + 1) ** 2
        initial = {"yPv": initialY, "xPv": initialX}

        def mock_get(pvs, **kwargs):
            return_vals = []
            for pv in pvs:
                return_vals.append(initial[pv])
            return return_vals

        catools.caget.side_effect = mock_get
        c = self.create_block(
            CAWaveformTablePart(
                name="attrname",
                description="desc",
                pv_list=(
                    "yPv",
                    "xPv",
                ),
                name_list=(
                    "yData",
                    "xData",
                ),
                timeout=-1,
            ),
            "withDisplayFromPv",
        )

        assert isinstance(c.attrname.value, Table)

        assert c.attrname.value["yData"] == [1.2, 2.2, 3.2]
        assert c.attrname.meta.description == "desc"
        assert not c.attrname.meta.writeable
        assert c.attrname.meta.elements["yData"].display.limitLow == np.e
        assert c.attrname.meta.elements["yData"].display.limitHigh == 10.0
        assert c.attrname.meta.elements["yData"].display.precision == 7
        assert c.attrname.meta.elements["xData"].display.limitLow == 0.0
        assert c.attrname.meta.elements["xData"].display.limitHigh == np.pi
        assert c.attrname.meta.elements["xData"].display.units == "s"

        catools.caget.assert_called_with(
            ("yPv", "xPv"),
            datatype=catools.DBR_DOUBLE,
            format=catools.FORMAT_CTRL,
            throw=True,
        )

        catools.caget.reset_mock()

    def test_cadouble(self, catools):
        from malcolm.modules.ca.parts import CADoublePart

        class Initial(float):
            ok = True
            severity = 0
            precision = 99
            lower_disp_limit = 189
            upper_disp_limit = 1527
            units = "tests"

        catools.caget.side_effect = [[Initial(5.2)], [Initial(5.2)]]
        b = self.create_block(
            CADoublePart(
                name="attrname", description="desc", rbv="pv", display_from_pv=False
            ),
            "noDisplayFromPv",
        )
        assert b.attrname.value == 5.2
        assert b.attrname.meta.description == "desc"
        assert not b.attrname.meta.writeable

        assert b.attrname.meta.display.limitLow == 0.0
        assert b.attrname.meta.display.limitHigh == 0.0
        assert b.attrname.meta.display.precision == 8
        assert b.attrname.meta.display.units == ""

        catools.caget.assert_called_once_with(
            ["pv"], datatype=catools.DBR_DOUBLE, format=catools.FORMAT_CTRL, throw=True
        )

        li = []
        b.attrname.subscribe_value(li.append)
        b._context.sleep(0.1)
        assert li == [5.2]

        catools.camonitor.assert_called_once()
        callback = catools.camonitor.call_args[0][1]
        callback(Initial(8.7))
        callback(Initial(8.8))
        assert b.attrname.value == 8.8

        # TODO: why does this seg fault on travis VMs when cothread is
        # stack sharing?
        b._context.sleep(0.1)
        assert li == [5.2, 8.7, 8.8]

        c = self.create_block(
            CADoublePart(name="attrname", description="desc", rbv="pv"),
            "withDisplayFromPv",
        )

        assert c.attrname.meta.display.limitLow == 189
        assert c.attrname.meta.display.limitHigh == 1527
        assert c.attrname.meta.display.precision == 99
        assert c.attrname.meta.display.units == "tests"

    def test_calongarray(self, catools):
        from malcolm.modules.ca.parts import CALongArrayPart

        class Initial(np.ndarray):
            ok = True
            severity = 0

        initial = Initial(dtype=np.int32, shape=(4,))
        initial[:] = [5, 6, 7, 8]

        catools.caget.side_effect = [[initial]]
        b = self.create_block(
            CALongArrayPart(
                name="attrname", description="desc", pv="pv", widget=Widget.TEXTINPUT
            )
        )
        assert list(b.attrname.value) == [5, 6, 7, 8]
        assert b.attrname.meta.tags == ["widget:textinput", "config:1"]
        assert b.attrname.meta.writeable
        catools.caget.assert_called_once_with(
            ["pv"], datatype=catools.DBR_LONG, format=catools.FORMAT_CTRL, throw=True
        )
        catools.caget.reset_mock()

        class Update(np.ndarray):
            ok = True
            severity = 0

        update = Update(shape=(2,), dtype=np.int32)
        update[:] = [4, 5]

        catools.caget.side_effect = [update]
        b.attrname.put_value([4, 4.2])
        catools.caput.assert_called_once_with(
            "pv", ANY, datatype=catools.DBR_LONG, timeout=10.0, wait=True
        )
        assert list(catools.caput.call_args[0][1]) == [4, 4]
        catools.caget.assert_called_once_with(
            "pv", datatype=catools.DBR_LONG, format=catools.FORMAT_TIME, throw=True
        )
        assert list(b.attrname.value) == [4, 5]
        assert b.attrname.alarm.is_ok()

    def test_calong(self, catools):
        from malcolm.modules.ca.parts import CALongPart

        class Initial(int):
            ok = True
            severity = 0

        catools.caget.side_effect = [[Initial(3)]]
        b = self.create_block(CALongPart(name="attrname", description="desc", pv="pv"))
        assert b.attrname.value == 3
        assert b.attrname.meta.description == "desc"
        assert b.attrname.meta.writeable
        catools.caget.assert_called_once_with(
            ["pv"], datatype=catools.DBR_LONG, format=catools.FORMAT_CTRL, throw=True
        )

    def test_castring(self, catools):
        from malcolm.modules.ca.parts import CAStringPart

        class Initial(str):
            ok = True
            severity = 0

        catools.caget.side_effect = [[Initial("thing")]]
        b = self.create_block(
            CAStringPart(name="attrname", description="desc", rbv="pv")
        )
        assert b.attrname.value == "thing"
        assert b.attrname.meta.description == "desc"
        assert not b.attrname.meta.writeable
        catools.caget.assert_called_once_with(
            ["pv"], datatype=catools.DBR_STRING, format=catools.FORMAT_CTRL, throw=True
        )

    def test_init_no_pv_no_rbv(self, catools):
        from malcolm.modules.ca.parts import CABooleanPart

        # create test for no pv or rbv
        with self.assertRaises(ValueError):
            CABooleanPart(name="attrname", description="desc")
