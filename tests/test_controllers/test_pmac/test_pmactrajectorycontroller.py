import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, call
import time

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# module imports
from malcolm.controllers.pmac import PMACTrajectoryController
from malcolm.controllers.builtin import DefaultController
from malcolm.core import Process, SyncFactory
from malcolm.parts.demo.dummymotorpart import DummyMotorPart
from malcolm.parts.demo.dummytrajectorypart import DummyTrajectoryPart
from scanpointgenerator import LineGenerator, CompoundGenerator


class TestPMACTrajectoryController(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.process = Process("proc", SyncFactory("sf"))
        self.traj = DummyTrajectoryPart(self.process)
        self.parts = dict(traj=self.traj)
        for m, cs_axis in zip("xyz", "ABC"):
            params = DummyMotorPart.MethodMeta.prepare_input_map(
                dict(cs_axis=cs_axis))
            self.parts[m] = DummyMotorPart(self.process, params)
        self.c = PMACTrajectoryController('block', self.process, self.parts)
        self.b = self.c.block
        self.b.reset()

    def test_init(self):
        self.assertEqual(self.c.hook_names, {
            self.c.ReportCSInfo: "ReportCSInfo",
            self.c.BuildProfile: "BuildProfile",
            self.c.RunProfile: "RunProfile",
            DefaultController.Resetting: "Resetting",
            DefaultController.Disabling: "Disabling",
        })
        self.assertEqual(self.c.parts, self.parts)

    def test_get_cs_port(self):
        cs_port, axis_mapping = self.c.get_cs_port(["x", "z"])
        self.assertEqual(cs_port, "CS1")
        self.assertEqual(axis_mapping, dict(x="A", z="C"))

    def test_configure_run(self):
        self.assertEqual(self.b.state, "Idle")
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate_direction=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        gen = CompoundGenerator([ys, xs], [], [])
        trajx = self.traj.axis_rbv["A"]
        trajx.set_value = Mock(wraps=trajx.set_value)
        trajy = self.traj.axis_rbv["B"]
        trajy.set_value = Mock(wraps=trajy.set_value)
        self.b.configure(
            generator=gen,
            axes_to_move=["x", "y"],
            exposure=0.05)
        self.assertEqual(self.b.state, "Ready")
        trajx.set_value.assert_called_once_with(-0.625)
        trajx.set_value.reset_mock()
        trajy.set_value.assert_called_once_with(0.0)
        trajy.set_value.reset_mock()
        start = time.time()
        self.b.run()
        end = time.time()
        self.assertEqual(trajx.set_value.call_args_list, [
            call(-0.125),
            call(0.0),
            call(0.125),
            call(0.25),
            call(0.375),
            call(0.5),
            call(0.625),

            call(0.625),
            call(0.5),
            call(0.375),
            call(0.25),
            call(0.125),
            call(0.0),
            call(-0.125),
            call(-0.625)])
        self.assertEqual(trajy.set_value.call_args_list, [
            call(0.0),
            call(0.0),
            call(0.0),
            call(0.0),
            call(0.0),
            call(0.0),
            call(0.0),

            call(0.1),
            call(0.1),
            call(0.1),
            call(0.1),
            call(0.1),
            call(0.1),
            call(0.1),
            call(0.1)])
        self.assertEqual(self.b.state, "Idle")
        expected = 3 * 2 * 0.05 + 0.1 + 2 * self.parts["x"].get_acceleration_time()
        self.assertAlmostEqual(end - start, expected, delta=0.05)


if __name__ == "__main__":
    unittest.main(verbosity=2)
