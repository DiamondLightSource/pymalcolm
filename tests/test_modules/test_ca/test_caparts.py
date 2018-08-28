import unittest
from mock import patch, ANY

import numpy as np

from malcolm.core import AlarmSeverity, Process, Widget
from malcolm.modules.builtin.controllers import StatefulController
from malcolm.modules.ca.parts import CABooleanPart, CACharArrayPart, \
    CAChoicePart, CADoubleArrayPart, CADoublePart, CALongArrayPart, \
    CALongPart, CAStringPart


@patch("malcolm.modules.ca.util.CaToolsHelper._instance")
class TestCAParts(unittest.TestCase):

    def setUp(self):
        self.process = Process("proc")
        self.process.start()

    def create_block(self, p):
        c = StatefulController("mri")
        c.add_part(p)
        self.process.add_controller(c)
        b = self.process.block_view("mri")
        return b

    def tearDown(self):
        self.process.stop(timeout=2)

    def test_caboolean(self, catools):

        class Initial(int):
            ok = True
            severity = 0

        catools.checking_caget.side_effect = [[Initial(0), Initial(0)]]
        b = self.create_block(CABooleanPart(
                name="attrname", description="desc", pv="pv", rbv_suffix="2"))
        assert b.attrname.value is False
        assert b.attrname.meta.description == "desc"
        assert b.attrname.meta.writeable
        catools.checking_caget.assert_called_once_with(
            ["pv2", 'pv'], datatype=catools.DBR_LONG,
            format=catools.FORMAT_CTRL)

        class Update(int):
            ok = True
            severity = 0
            raw_stamp = (34, 4355)

        catools.caget.side_effect = [Update(1)]
        b.attrname.put_value(True)
        catools.caput.assert_called_once_with(
            "pv", 1, datatype=catools.DBR_LONG, timeout=10.0, wait=True)
        catools.caget.assert_called_once_with(
            "pv2", datatype=catools.DBR_LONG, format=catools.FORMAT_TIME)
        assert b.attrname.value is True
        assert b.attrname.alarm.is_ok()
        assert b.attrname.timeStamp.to_time() == 34.000004355

    def test_cachararray(self, catools):
        class Initial(str):
            ok = True
            severity = 1

        catools.checking_caget.side_effect = [[Initial("long_and_bad_string")]]
        b = self.create_block(CACharArrayPart(
            name="cattr", description="desc", rbv="pvr"))
        assert b.cattr.value == "long_and_bad_string"
        assert b.cattr.alarm.severity == AlarmSeverity.MINOR_ALARM
        catools.checking_caget.assert_called_once_with(
            ["pvr"], datatype=catools.DBR_CHAR_STR, format=catools.FORMAT_CTRL)

    def test_cachoice(self, catools):

        class Initial(int):
            ok = True
            severity = 0
            enums = ["a", "b", "c"]

        catools.checking_caget.side_effect = [[Initial(1), Initial(2)]]
        b = self.create_block(CAChoicePart(
            name="attrname", description="desc", pv="pv", rbv="rbv"))
        assert b.attrname.value is "b"
        assert b.attrname.meta.description == "desc"
        assert b.attrname.meta.writeable
        catools.checking_caget.assert_called_once_with(
            ["rbv", 'pv'], datatype=catools.DBR_ENUM,
            format=catools.FORMAT_CTRL)

        class Update(int):
            ok = True
            severity = 2
            raw_stamp = (34, 4355)

        catools.caget.side_effect = [Update(0)]
        b.attrname.put_value("c")
        catools.caput.assert_called_once_with(
            "pv", 2, datatype=catools.DBR_ENUM, timeout=10.0, wait=True)
        catools.caget.assert_called_once_with(
            "rbv", datatype=catools.DBR_ENUM, format=catools.FORMAT_TIME)
        assert b.attrname.value is "a"
        assert b.attrname.alarm.severity == AlarmSeverity.MAJOR_ALARM
        assert b.attrname.timeStamp.to_time() == 34.000004355
        catools.caget.reset_mock()
        catools.caput.reset_mock()

        catools.caget.side_effect = [Update(1)]
        b.attrname.put_value(1)
        catools.caput.assert_called_once_with(
            "pv", 1, datatype=catools.DBR_ENUM, timeout=10.0, wait=True)
        assert b.attrname.value is "b"

    def test_cadoublearray(self, catools):
        class Initial(np.ndarray):
            ok = True
            severity = 0
        initial = Initial(dtype=np.float64, shape=(3,))
        initial[:] = np.arange(3) + 1.2

        catools.checking_caget.side_effect = [[initial]]
        b = self.create_block(CADoubleArrayPart(
            name="attrname", description="desc", pv="pv",
            timeout=-1))
        assert list(b.attrname.value) == [1.2, 2.2, 3.2]
        assert b.attrname.meta.description == "desc"
        assert b.attrname.meta.writeable
        catools.checking_caget.assert_called_once_with(
            ["pv"], datatype=catools.DBR_DOUBLE,
            format=catools.FORMAT_CTRL)

        class Update(np.ndarray):
            ok = False

        catools.caget.side_effect = [Update(shape=(6,))]
        b.attrname.put_value([])
        catools.caput.assert_called_once_with(
            "pv", ANY, datatype=catools.DBR_DOUBLE, timeout=None, wait=True)
        assert list(catools.caput.call_args[0][1]) == []
        catools.caget.assert_called_once_with(
            "pv", datatype=catools.DBR_DOUBLE, format=catools.FORMAT_TIME)
        assert list(b.attrname.value) == []
        assert b.attrname.alarm.severity == AlarmSeverity.INVALID_ALARM

    def test_cadouble(self, catools):

        class Initial(float):
            ok = True
            severity = 0

        catools.checking_caget.side_effect = [[Initial(5.2)]]
        b = self.create_block(CADoublePart(
            name="attrname", description="desc", rbv="pv"))
        assert b.attrname.value == 5.2
        assert b.attrname.meta.description == "desc"
        assert not b.attrname.meta.writeable
        catools.checking_caget.assert_called_once_with(
            ['pv'], datatype=catools.DBR_DOUBLE,
            format=catools.FORMAT_CTRL)

        l = []
        b.attrname.subscribe_value(l.append)
        b._context.sleep(0.1)
        assert l == [5.2]

        catools.camonitor.assert_called_once()
        callback = catools.camonitor.call_args[0][1]
        callback(Initial(8.7))
        callback(Initial(8.8))
        assert b.attrname.value == 8.8

        b._context.sleep(0.1)
        assert l == [5.2, 8.7, 8.8]

    def test_calongarray(self, catools):
        class Initial(np.ndarray):
            ok = True
            severity = 0
        initial = Initial(dtype=np.int32, shape=(4,))
        initial[:] = [5, 6, 7, 8]

        catools.checking_caget.side_effect = [[initial]]
        b = self.create_block(CALongArrayPart(
            name="attrname", description="desc", pv="pv",
            widget=Widget.TEXTINPUT))
        assert list(b.attrname.value) == [5, 6, 7, 8]
        assert b.attrname.meta.tags == ["widget:textinput", 'config:1']
        assert b.attrname.meta.writeable
        catools.checking_caget.assert_called_once_with(
            ["pv"], datatype=catools.DBR_LONG,
            format=catools.FORMAT_CTRL)

        class Update(np.ndarray):
            ok = True
            severity = 0
        update = Update(shape=(2,), dtype=np.int32)
        update[:] = [4, 5]

        catools.caget.side_effect = [update]
        b.attrname.put_value([4, 4.2])
        catools.caput.assert_called_once_with(
            "pv", ANY, datatype=catools.DBR_LONG, timeout=10.0, wait=True)
        assert list(catools.caput.call_args[0][1]) == [4, 4]
        catools.caget.assert_called_once_with(
            "pv", datatype=catools.DBR_LONG, format=catools.FORMAT_TIME)
        assert list(b.attrname.value) == [4, 5]
        assert b.attrname.alarm.is_ok()

    def test_calong(self, catools):

        class Initial(int):
            ok = True
            severity = 0

        catools.checking_caget.side_effect = [[Initial(3)]]
        b = self.create_block(CALongPart(
            name="attrname", description="desc", pv="pv"))
        assert b.attrname.value == 3
        assert b.attrname.meta.description == "desc"
        assert b.attrname.meta.writeable
        catools.checking_caget.assert_called_once_with(
            ['pv'], datatype=catools.DBR_LONG,
            format=catools.FORMAT_CTRL)

    def test_castring(self, catools):

        class Initial(str):
            ok = True
            severity = 0

        catools.checking_caget.side_effect = [[Initial("thing")]]
        b = self.create_block(CAStringPart(
            name="attrname", description="desc", rbv="pv"))
        assert b.attrname.value == "thing"
        assert b.attrname.meta.description == "desc"
        assert not b.attrname.meta.writeable
        catools.checking_caget.assert_called_once_with(
            ['pv'], datatype=catools.DBR_STRING,
            format=catools.FORMAT_CTRL)

    def test_init_no_pv_no_rbv(self, catools):
        # create test for no pv or rbv
        with self.assertRaises(ValueError):
            CABooleanPart(name="attrname", description="desc")

