import unittest
from mock import patch

from malcolm.core import Process, AlarmSeverity
from malcolm.modules.builtin.controllers import StatefulController
from malcolm.modules.pmac.parts import CompoundMotorCSPart


class castr(str):
    ok = True
    severity = 0


class TestCompoundMotorCSPart(unittest.TestCase):
    @patch("malcolm.modules.pmac.parts.compoundmotorcspart.catools")
    def setUp(self, catools):
        self.catools = catools
        catools.caget.side_effect = [[castr("@asyn(BRICK1CS1,2)")]]
        self.process = Process("proc")
        self.o = CompoundMotorCSPart("cs", "PV:PRE.OUT")
        c = StatefulController("mri")
        c.add_part(self.o)
        self.process.add_controller(c)
        self.b = self.process.block_view("mri")
        self.process.start()
        self.addCleanup(self.process.stop)

    def test_init(self):
        self.catools.caget.assert_called_once_with(
            ["PV:PRE.OUT"], format=self.catools.FORMAT_CTRL)
        assert list(self.b) == [
            'meta', 'health', 'state', 'disable', 'reset', 'cs']
        assert self.b.cs.value == "BRICK1CS1,B"

    def test_update_good(self):
        update = castr("@asyn(BRICK1CS1, 3)")
        self.o._update_value(update)
        assert self.b.cs.value == "BRICK1CS1,C"

    def test_update_bad(self):
        update = castr("@asyn(BRICK1CS1, 3)")
        update.ok = False
        self.o._update_value(update)
        assert self.b.cs.value == ""
        assert self.b.cs.alarm.severity == AlarmSeverity.INVALID_ALARM

