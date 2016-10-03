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
        self.o.make_panda_block("P:PCOMP", "PCOMP", BlockData(1, "", fields))
        fields = OrderedDict()
        fields["INP"] = FieldData("bit_mux", "", "Input", ["ZERO", "TTLIN.VAL"])
        fields["START"] = FieldData("param", "pos", "Start position", [])
        fields["OUT"] = FieldData("pos_out", "", "Output", ["No", "Capture"])
        self.o.make_panda_block("P:COUNTER", "COUNTER", BlockData(1, "", fields))
        fields = OrderedDict()
        fields["VAL"] = FieldData("bit_out", "", "Output", [])
        self.o.make_panda_block("P:TTLIN", "TTLIN", BlockData(1, "", fields))
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

    def test_initial_changes(self):
        pcomp = self.o._blocks["PCOMP"]
        self.assertEqual(pcomp.INP, "ZERO")
        self.assertEqual(pcomp.INP_VAL, 0.0)
        self.assertEqual(pcomp.START, 0.0)
        self.assertEqual(pcomp.STEP, 0.0)
        self.assertEqual(pcomp.OUT, False)
        counter = self.o._blocks["COUNTER"]
        self.assertEqual(counter.INP, "ZERO")
        self.assertEqual(counter.INP_DELAY, 0)
        self.assertEqual(counter.INP_VAL, False)
        self.assertEqual(counter.OUT, 0.0)
        self.assertEqual(counter.OUT_SCALE, 1.0)
        self.assertEqual(counter.OUT_OFFSET, 0.0)
        self.assertEqual(counter.OUT_UNITS, "")
        ttlin = self.o._blocks["TTLIN"]
        self.assertEqual(ttlin.VAL, False)

    def test_rewiring(self):
        counter = self.o._blocks["COUNTER"]
        pcomp = self.o._blocks["PCOMP"]
        self.o.handle_changes({"COUNTER.OUT": 32.0})
        self.assertEqual(counter.OUT, 32.0)
        self.o.handle_changes({"PCOMP.INP": "COUNTER.OUT"})
        self.assertEqual(pcomp.INP, "COUNTER.OUT")
        self.assertEqual(pcomp.INP_VAL, 32.0)
        self.o.handle_changes({"PCOMP.INP": "ZERO"})
        self.assertEqual(pcomp.INP, "ZERO")
        self.assertEqual(pcomp.INP_VAL, 0.0)

    def test_scale_offset_following(self):
        pcomp = self.o._blocks["PCOMP"]
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
        self.assertEqual(pcomp.INP, "COUNTER.OUT")
        self.assertEqual(pcomp.INP_VAL, 0.0)
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
