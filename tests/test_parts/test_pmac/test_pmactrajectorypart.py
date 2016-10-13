import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, call

Mock = MagicMock

from malcolm.parts.pmac.pmactrajectorypart import PMACTrajectoryPart, MotorInfo
from scanpointgenerator import LineGenerator, CompoundGenerator
from scanpointgenerator.fixeddurationmutator import FixedDurationMutator
from malcolm.core import Table


class TestPMACTrajectoryPart(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.process = Mock()
        self.child = Mock()

        def getitem(name):
            return name

        self.child.__getitem__.side_effect = getitem
        self.params = Mock()
        self.process.get_block.return_value = self.child
        self.o = PMACTrajectoryPart(self.process, self.params)
        list(self.o.create_attributes())

    def test_init(self):
        self.process.get_block.assert_called_once_with(self.params.child)
        self.assertEqual(self.o.child, self.child)

    def check_resolutions_and_use(self, args, useB=True):
        expected = {
            self.child["resolutionA"]: 0.001,
            self.child["offsetA"]: 0.0,
            self.child["useA"]: True,
            self.child["useB"]: useB,
            self.child["useC"]: False,
            self.child["useU"]: False,
            self.child["useV"]: False,
            self.child["useW"]: False,
            self.child["useX"]: False,
            self.child["useY"]: False,
            self.child["useZ"]: False}
        if useB:
            expected.update({
                self.child["resolutionB"]: 0.001,
                self.child["offsetB"]: 0.0,
            })
        self.assertEqual(args, expected)

    def do_configure(self, axes_to_scan, completed_steps=0, x_pos=0.5):
        task = Mock()
        part_info = dict(
            x=MotorInfo(
                cs_axis="A",
                cs_port="CS1",
                acceleration_time=0.1,
                resolution=0.001,
                offset=0,
                max_velocity=1.0,
                current_position=x_pos),
            y=MotorInfo(
                cs_axis="B",
                cs_port="CS1",
                acceleration_time=0.1,
                resolution=0.001,
                offset=0,
                max_velocity=1.0,
                current_position=0.0)
        )
        steps_to_do = 3 * len(axes_to_scan)
        params = Mock()
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate_direction=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        mutator = FixedDurationMutator(1.0)
        params.generator = CompoundGenerator([ys, xs], [], [mutator])
        params.axesToMove = axes_to_scan
        self.o.configure(task, completed_steps, steps_to_do, part_info, params)
        return task

    def test_configure(self):
        task = self.do_configure(axes_to_scan=["x", "y"])
        self.assertEqual(task.put.call_count, 4)
        self.assertEqual(task.post.call_count, 2)
        self.assertEqual(task.post_async.call_count, 1)
        self.check_resolutions_and_use(task.put.call_args_list[0][0][0])
        self.assertEqual(task.put.call_args_list[1][0][0], {
            self.child["time_array"]: [100000, 437500, 100000],
            self.child["velocity_mode"]: [2, 1, 3],
            self.child["user_programs"]: [0, 0, 0],
            self.child["num_points"]: 3,
            self.child["positionsA"]: [0.45,
                                       -0.087500000000000008,
                                       -0.1375],
            self.child["positionsB"]: [0.0, 0.0, 0.0]})
        self.assertEqual(task.post.call_args_list[0],
                         call(self.child["build_profile"]))
        self.assertEqual(task.post_async.call_args_list[0],
                         call(self.child["execute_profile"]))
        self.assertEqual(task.post.call_args_list[1],
                         call(self.child["build_profile"]))
        self.check_resolutions_and_use(task.put.call_args_list[2][0][0])
        self.assertEqual(task.put.call_args_list[3][0][0], {
            self.child["time_array"]: [
                100000, 500000, 500000, 500000, 500000, 500000, 500000, 100000,
                100000, 500000, 500000, 500000, 500000, 500000, 500000, 100000],
            self.child["velocity_mode"]: [
                2, 0, 0, 0, 0, 0, 1, 0,
                2, 0, 0, 0, 0, 0, 1, 3],
            self.child["user_programs"]: [
                3, 4, 3, 4, 3, 4, 2, 8,
                3, 4, 3, 4, 3, 4, 2, 8],
            self.child["num_points"]: 16,
            self.child["positionsA"]: [
                -0.125, 0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.6375,
                0.625, 0.5, 0.375, 0.25, 0.125, 0.0, -0.125, -0.1375],
            self.child["positionsB"]: [
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.05,
                0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]})

    def test_run(self):
        task = Mock()
        update = Mock()
        self.o.run(task, update)
        task.subscribe.assert_called_once_with(
            self.child["points_scanned"], self.o.update_step, update)
        task.post.assert_called_once_with(self.child["execute_profile"])

    def test_multi_run(self):
        self.do_configure(axes_to_scan=["x"])
        self.assertEqual(self.o.completed_steps_lookup,
                         [0, 0, 1, 1, 2, 2, 3, 3])

        task = self.do_configure(
            axes_to_scan=["x"], completed_steps=3, x_pos=0.6375)
        self.assertEqual(task.put.call_count, 2)
        self.assertEqual(task.post.call_count, 1)
        self.check_resolutions_and_use(task.put.call_args_list[0][0][0],
                                       useB=False)
        self.assertEqual(task.put.call_args_list[1][0][0], {
            self.child["time_array"]: [
                100000, 500000, 500000, 500000, 500000, 500000, 500000, 100000],
            self.child["velocity_mode"]: [2, 0, 0, 0, 0, 0, 1, 3],
            self.child["user_programs"]: [3, 4, 3, 4, 3, 4, 2, 8],
            self.child["num_points"]: 8,
            self.child["positionsA"]: [0.625, 0.5, 0.375, 0.25, 0.125, 0.0,
                                       -0.125, -0.1375],
        })

    def test_long_move(self):
        task = self.do_configure(axes_to_scan=["x"], x_pos=-10.1375)
        self.assertEqual(task.put.call_args_list[1][0][0], {
            self.child["time_array"]: [
                100000, 3266667, 3266666, 3266667, 100000],
            self.child["velocity_mode"]: [
                2, 1, 1, 1, 3],
            self.child["user_programs"]: [
                0, 0, 0, 0, 0],
            self.child["num_points"]: 5,
            self.child["positionsA"]: [
                -10.087499999999999, -6.7875, -3.4875, -0.1875, -0.1375],
        })

    def future_long_scan(self):
        task = Mock()
        part_info = dict(
            x=MotorInfo(
                cs_axis="A",
                cs_port="CS1",
                acceleration_time=0.1,
                resolution=0.001,
                offset=0,
                max_velocity=1.0,
                current_position=0.0),
            y=MotorInfo(
                cs_axis="B",
                cs_port="CS1",
                acceleration_time=0.1,
                resolution=0.001,
                offset=0,
                max_velocity=1.0,
                current_position=0.0)
        )
        steps_to_do = 2000 * 2000
        params = Mock()
        xs = LineGenerator("x", "mm", 0.0, 0.5, 2000, alternate_direction=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2000)
        mutator = FixedDurationMutator(0.005)
        params.generator = CompoundGenerator([ys, xs], [], [mutator])
        params.axesToMove = ["x", "y"]
        completed_steps = 0
        self.o.configure(task, completed_steps, steps_to_do, part_info, params)


if __name__ == "__main__":
    unittest.main(verbosity=2)
