import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, call

Mock=MagicMock

from malcolm.parts.pmac.pmactrajectorypart import PMACTrajectoryPart, \
    info_table_meta
from scanpointgenerator import LineGenerator, CompoundGenerator
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

    def test_init(self):
        self.process.get_block.assert_called_once_with(self.params.child)
        self.assertEqual(self.o.child, self.child)

    def check_resolutions_and_use(self, args):
        self.assertEqual(args, {
            self.child["resolutionA"]: 0.001,
            self.child["resolutionB"]: 0.001,
            self.child["offsetA"]: 0.0,
            self.child["offsetB"]: 0.0,
            self.child["useA"]: True,
            self.child["useB"]: True,
            self.child["useC"]: False,
            self.child["useU"]: False,
            self.child["useV"]: False,
            self.child["useW"]: False,
            self.child["useX"]: False,
            self.child["useY"]: False,
            self.child["useZ"]: False})

    def test_configure(self):
        params = Mock()
        params.info_table = Table(info_table_meta)
        params.info_table.name = ["x", "y"]
        params.info_table.cs_axis = ["A", "B"]
        params.info_table.cs_port = ["CS1", "CS1"]
        params.info_table.acceleration_time = [0.1, 0.1]
        params.info_table.resolution = [0.001, 0.001]
        params.info_table.offset = [0, 0]
        params.info_table.max_velocity = [1.0, 1.0]
        params.info_table.current_position = [0.5, 0.0]
        params.start_step = 0
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate_direction=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        params.generator = CompoundGenerator([ys, xs], [], [])
        params.exposure = 1.0
        params.axes_to_move = ["x", "y"]
        task = Mock()
        self.o.configure(task, params)
        self.assertEqual(task.put.call_count, 4)
        self.assertEqual(task.post.call_count, 3)
        self.check_resolutions_and_use(task.put.call_args_list[0][0][0])
        self.assertEqual(task.put.call_args_list[1][0][0], {
            self.child["time_array"]: [400, 1750, 400],
            self.child["velocity_mode"]: [2, 1, 3],
            self.child["user_programs"]: [0, 0, 0],
            self.child["num_points"]: 3,
            self.child["positionsA"]: [0.45,
                                       -0.087500000000000008,
                                       -0.1375],
            self.child["positionsB"]: [0.0, 0.0, 0.0]})
        self.assertEqual(task.post.call_args_list[0],
                         call(self.child["build_profile"]))
        self.assertEqual(task.post.call_args_list[1],
                         call(self.child["execute_profile"]))
        self.check_resolutions_and_use(task.put.call_args_list[2][0][0])
        self.assertEqual(task.put.call_args_list[3][0][0], {
            self.child["time_array"]: [
                400, 2000, 2000, 2000, 2000, 2000, 2000, 400,
                400, 2000, 2000, 2000, 2000, 2000, 2000, 400],
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
        self.o.run(task)
        task.subscribe.assert_called_once_with(
            self.child["points_scanned"], self.o.update_step)
        task.post.assert_called_once_with(self.child["execute_profile"])

    def test_build_next_stage(self):
        self.test_configure()
        self.o.points_built = 4
        task = Mock()
        self.o.build_next_stage(task)
        self.assertEqual(task.put.call_count, 4)
        self.assertEqual(task.post.call_count, 3)
        self.check_resolutions_and_use(task.put.call_args_list[0][0][0])
        self.assertEqual(task.put.call_args_list[1][0][0], {
            self.child["time_array"]: [400, 1300, 400],
            self.child["velocity_mode"]: [2, 1, 3],
            self.child["user_programs"]: [0, 0, 0],
            self.child["num_points"]: 3,
            self.child["positionsA"]: [-0.087500000000000008,
                                       0.33750000000000002,
                                       0.38750000000000001],
            self.child["positionsB"]: [0.1, 0.1, 0.1]})
        self.assertEqual(task.post.call_args_list[0],
                         call(self.child["build_profile"]))
        self.assertEqual(task.post.call_args_list[1],
                         call(self.child["execute_profile"]))
        self.check_resolutions_and_use(task.put.call_args_list[2][0][0])
        self.assertEqual(task.put.call_args_list[3][0][0], {
            self.child["time_array"]: [400, 2000, 2000, 2000, 2000, 400],
            self.child["velocity_mode"]: [2, 0, 0, 0, 1, 3],
            self.child["user_programs"]: [3, 4, 3, 4, 2, 8],
            self.child["num_points"]: 6,
            self.child["positionsA"]: [0.375, 0.25, 0.125, 0.0, -0.125, -0.1375],
            self.child["positionsB"]: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
