import os
import sys
from collections import OrderedDict

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import call, Mock

from malcolm.parts.pandabox.pandaboxpoller import PandABoxPoller
from malcolm.parts.pandabox.pandaboxcontrol import BlockData, FieldData


class PandABoxPollerTest(unittest.TestCase):
    def setUp(self):
        self.process = Mock()
        self.control = Mock()
        self.o = PandABoxPoller(self.process, self.control)
        fields = OrderedDict()
        fields["INP"] = FieldData("pos_mux", "", "Input A", ["ZERO", "COUNTER.OUT"])
        fields["START"] = FieldData("param", "pos", "Start position", [])
        fields["STEP"] = FieldData("param", "relative_pos", "Step position", [])
        fields["OUT"] = FieldData("bit_out", "", "Output", [])
        self.pcomp = self.o.make_panda_block(
            "P:PCOMP", "PCOMP", BlockData(1, "", fields))
        fields = OrderedDict()
        fields["INP"] = FieldData("bit_mux", "", "Input", ["ZERO", "TTLIN.VAL"])
        fields["START"] = FieldData("param", "pos", "Start position", [])
        fields["OUT"] = FieldData("pos_out", "", "Output", ["No", "Capture"])
        self.counter = self.o.make_panda_block(
            "P:COUNTER", "COUNTER", BlockData(1, "", fields))
        fields = OrderedDict()
        fields["VAL"] = FieldData("bit_out", "", "Output", [])
        self.ttlin = self.o.make_panda_block(
            "P:TTLIN", "TTLIN", BlockData(1, "", fields))
        changes = OrderedDict()
        changes["PCOMP.INP"] = "ZERO"
        for field_name in ("START", "STEP"):
            changes["PCOMP.%s" % field_name] = "0"
            changes["PCOMP.%s.SCALE" % field_name] = "1"
            changes["PCOMP.%s.OFFSET" % field_name] = "0"
            changes["PCOMP.%s.UNITS" % field_name] = ""
        changes["PCOMP.OUT"] = "0"
        changes["COUNTER.INP"] = "ZERO"
        changes["COUNTER.INP.DELAY"] = "0"
        changes["COUNTER.OUT"] = "0"
        changes["COUNTER.OUT.SCALE"] = "1"
        changes["COUNTER.OUT.OFFSET"] = "0"
        changes["COUNTER.OUT.UNITS"] = ""
        changes["TTLIN.VAL"] = "0"
        self.o.handle_changes(changes)
        # Once more to let the bit_outs toggle back
        self.o.handle_changes({})

    def test_initial_changes(self):
        pcomp = self.pcomp
        self.assertEqual(pcomp.inp, "ZERO")
        self.assertEqual(pcomp.inpVal, 0.0)
        self.assertEqual(pcomp.start, 0.0)
        self.assertEqual(pcomp.step, 0.0)
        self.assertEqual(pcomp.out, False)
        counter = self.counter
        self.assertEqual(counter.inp, "ZERO")
        self.assertEqual(counter.inpDelay, 0)
        self.assertEqual(counter.inpVal, False)
        self.assertEqual(counter.out, 0.0)
        self.assertEqual(counter.outScale, 1.0)
        self.assertEqual(counter.outOffset, 0.0)
        self.assertEqual(counter.outUnits, "")
        ttlin = self.ttlin
        self.assertEqual(ttlin.val, False)

    def test_rewiring(self):
        pcomp = self.pcomp
        counter = self.counter
        self.o.handle_changes({"COUNTER.OUT": 32.0})
        self.assertEqual(counter.out, 32.0)
        self.o.handle_changes({"PCOMP.INP": "COUNTER.OUT"})
        self.assertEqual(pcomp.inp, "COUNTER.OUT")
        self.assertEqual(pcomp.inpVal, 32.0)
        self.o.handle_changes({"PCOMP.INP": "ZERO"})
        self.assertEqual(pcomp.inp, "ZERO")
        self.assertEqual(pcomp.inpVal, 0.0)

    def test_scale_offset_following(self):
        pcomp = self.pcomp
        self.assertEqual(self.control.send.call_args_list, [
            call('PCOMP.START.SCALE=1\n'),
            call('PCOMP.START.OFFSET=0\n'),
            call('PCOMP.START.UNITS=\n'),
            call('PCOMP.STEP.SCALE=1\n'),
            call('PCOMP.STEP.UNITS=\n'),
            call('COUNTER.START.SCALE=1\n'),
            call('COUNTER.START.OFFSET=0\n'),
            call('COUNTER.START.UNITS=\n'),
        ])
        self.control.send.reset_mock()
        self.o.handle_changes({"PCOMP.INP": "COUNTER.OUT"})
        self.assertEqual(pcomp.inp, "COUNTER.OUT")
        self.assertEqual(pcomp.inpVal, 0.0)
        self.assertEqual(self.control.send.call_args_list, [
            call('PCOMP.START.SCALE=1.0\n'),
            call('PCOMP.START.OFFSET=0.0\n'),
            call('PCOMP.START.UNITS=\n'),
            call('PCOMP.STEP.SCALE=1.0\n'),
            call('PCOMP.STEP.UNITS=\n')
        ])
        self.control.send.reset_mock()
        self.o.handle_changes({"COUNTER.OUT.OFFSET": "5.2"})
        self.assertEqual(self.control.send.call_args_list, [
            call('COUNTER.START.OFFSET=5.2\n'),
            call('PCOMP.START.OFFSET=5.2\n')
        ])
        self.control.send.reset_mock()
        self.o.handle_changes({"COUNTER.OUT.SCALE": "0.2"})
        self.assertEqual(self.control.send.call_args_list, [
            call('COUNTER.START.SCALE=0.2\n'),
            call('PCOMP.START.SCALE=0.2\n'),
            call('PCOMP.STEP.SCALE=0.2\n'),
        ])
        self.control.send.reset_mock()
        self.o.handle_changes({"PCOMP.INP": "ZERO"})
        self.assertEqual(self.control.send.call_args_list, [
            call('PCOMP.START.SCALE=1\n'),
            call('PCOMP.START.OFFSET=0\n'),
            call('PCOMP.START.UNITS=\n'),
            call('PCOMP.STEP.SCALE=1\n'),
            call('PCOMP.STEP.UNITS=\n')
        ])



if __name__ == "__main__":
    unittest.main(verbosity=2)
