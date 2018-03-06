import unittest
from mock import patch

from malcolm.core import Process, AlarmSeverity
from malcolm.modules.builtin.controllers import StatefulController
from malcolm.modules.pmac.parts import RawMotorCSPart


class castr(str):
    ok = True
    severity = 0


class caenum(int):
    ok = True
    severity = 0
    enums = ["ANYTHING", "BRICK1CS1", "BRICK1CS2"]


class TestRawMotorCSPart(unittest.TestCase):
    @patch("malcolm.modules.ca.util.CaToolsHelper._instance")
    def setUp(self, catools):
        self.catools = catools
        catools.checking_caget.side_effect = [[
            caenum(2), castr("I"),
            caenum(1), castr("A")
        ]]
        self.process = Process("proc")
        self.o = RawMotorCSPart("cs", "PV:PRE")
        c = StatefulController("mri")
        c.add_part(self.o)
        self.process.add_controller(c)
        self.b = self.process.block_view("mri")
        self.process.start()
        self.addCleanup(self.process.stop)

    def test_init(self):
        self.catools.checking_caget.assert_called_once_with(
            ["PV:PRE:CsPort", "PV:PRE:CsAxis", "PV:PRE:CsPort_RBV",
             "PV:PRE:CsAxis_RBV"], format=self.catools.FORMAT_CTRL)
        assert list(self.b) == [
            'meta', 'health', 'state', 'disable', 'reset', 'cs']
        assert self.b.cs.value == "BRICK1CS1,A"

    def test_update_axis(self):
        update = castr("I")
        self.o._update_value(update, 1)
        assert self.b.cs.value == "BRICK1CS1,I"

    def test_update_port(self):
        update = caenum(2)
        self.o._update_value(update, 0)
        assert self.b.cs.value == "BRICK1CS2,A"

    def test_update_disconnect(self):
        update = caenum(0)
        self.o._update_value(update, 0)
        assert self.b.cs.value == ""

    def test_update_bad(self):
        update = castr("")
        update.ok = False
        self.o._update_value(update, 1)
        assert self.b.cs.value == ""
        assert self.b.cs.alarm.severity == AlarmSeverity.INVALID_ALARM

    def test_caput(self):
        self.catools.caget.side_effect = [[caenum(2), castr("Y")]]
        self.o.caput("BRICK1CS2,X")
        self.catools.caput.assert_called_once_with(
            ['PV:PRE:CsPort', 'PV:PRE:CsAxis'], (2, 'X'), wait=True
        )
        assert self.b.cs.value == "BRICK1CS2,Y"

    def test_caput_none(self):
        self.catools.caget.side_effect = [[caenum(0), castr("")]]
        self.o.caput("")
        self.catools.caput.assert_called_once_with(
            ['PV:PRE:CsPort', 'PV:PRE:CsAxis'], (0, ''), wait=True
        )
        assert self.b.cs.value == ""
