import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, call, patch

Mock = MagicMock

from malcolm.parts.pmac.pmactrajectorypart import PMACTrajectoryPart, MotorInfo
from scanpointgenerator import LineGenerator, CompoundGenerator, \
    FixedDurationMutator


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

    def check_resolutions_and_use(self, args, useB=True):
        expected = dict(
            resolutionA=0.001,
            offsetA=0.0,
            useA=True,
            useB=useB,
            useC=False,
            useU=False,
            useV=False,
            useW=False,
            useX=False,
            useY=False,
            useZ=False)
        if useB:
            expected.update(dict(
                resolutionB=0.001,
                offsetB=0.0))
        self.assertEqual(args, expected)

    def make_part_info(self, x_pos=0.5, y_pos=0.0):
        part_info = dict(
            xpart=[MotorInfo(
                cs_axis="A",
                cs_port="CS1",
                acceleration_time=0.1,
                resolution=0.001,
                offset=0,
                max_velocity=1.0,
                current_position=x_pos,
                scannable="x",
            )],
            ypart=[MotorInfo(
                cs_axis="B",
                cs_port="CS1",
                acceleration_time=0.05,
                resolution=0.001,
                offset=0,
                max_velocity=1.0,
                current_position=y_pos,
                scannable="y"
            )]
        )
        return part_info

    def do_configure(self, axes_to_scan, completed_steps=0, x_pos=0.5, y_pos=0.0):
        part_info = self.make_part_info(x_pos, y_pos)
        task = Mock()
        steps_to_do = 3 * len(axes_to_scan)
        params = Mock()
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate_direction=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        mutator = FixedDurationMutator(1.0)
        params.generator = CompoundGenerator([ys, xs], [], [mutator])
        params.axesToMove = axes_to_scan
        self.o.configure(task, completed_steps, steps_to_do, part_info, params)
        return task

    def test_validate(self):
        params = Mock()
        mutator = FixedDurationMutator(0.0102)
        params.generator = CompoundGenerator([], [], [mutator])
        params.axesToMove = ["x"]
        part_info = self.make_part_info()
        ret = self.o.validate(None, part_info, params)
        expected = 0.010166
        self.assertEqual(ret[0].value.mutators[0].duration, expected)

    def test_configure(self):
        task = self.do_configure(axes_to_scan=["x", "y"])
        self.assertEqual(task.put_many.call_count, 4)
        self.assertEqual(task.post.call_count, 2)
        self.assertEqual(task.post_async.call_count, 1)
        self.assertEqual(task.put.call_count, 2)
        self.assertEqual(task.put.call_args_list[0],
                         call(self.child["cs"], "CS1"))
        self.check_resolutions_and_use(task.put_many.call_args_list[0][0][1])
        self.assertEqual(task.put_many.call_args_list[1][0][1], dict(
            timeArray=[100000, 537500, 100000],
            velocityMode=[2, 1, 3],
            userPrograms=[0, 0, 0],
            pointsToBuild=3,
            positionsA=[0.45, -0.08750000000000002, -0.1375],
            positionsB=[0.0, 0.0, 0.0]))
        self.assertEqual(task.post.call_args_list[0],
                         call(self.child["buildProfile"]))
        self.assertEqual(task.post_async.call_args_list[0],
                         call(self.child["executeProfile"]))
        self.assertEqual(task.post.call_args_list[1],
                         call(self.child["buildProfile"]))
        self.check_resolutions_and_use(task.put_many.call_args_list[2][0][1])
        self.assertEqual(task.put_many.call_args_list[3][0][1], dict(
            timeArray=[
                100000, 500000, 500000, 500000, 500000, 500000, 500000, 100000,
                100000, 500000, 500000, 500000, 500000, 500000, 500000, 100000],
            velocityMode=[
                2, 0, 0, 0, 0, 0, 1, 0,
                2, 0, 0, 0, 0, 0, 1, 3],
            userPrograms=[
                3, 4, 3, 4, 3, 4, 2, 8,
                3, 4, 3, 4, 3, 4, 2, 8],
            pointsToBuild=16,
            positionsA=[
                -0.125, 0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.6375,
                0.625, 0.5, 0.375, 0.25, 0.125, 0.0, -0.125, -0.1375],
            positionsB=[
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.05,
                0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]))
        self.assertEqual(task.put.call_args_list[1],
                         call(self.child["numPoints"], 18))

    def test_2_axis_move_to_start(self):
        task = self.do_configure(axes_to_scan=["x", "y"], x_pos=0.0, y_pos=0.2)
        self.assertEqual(task.put_many.call_count, 4)
        self.assertEqual(task.post.call_count, 2)
        self.assertEqual(task.post_async.call_count, 1)
        self.check_resolutions_and_use(task.put_many.call_args_list[0][0][1])
        self.assertEqual(task.put_many.call_args_list[1][0][1], dict(
            timeArray=[100000, 100000, 100000],
            velocityMode=[2, 1, 3],
            userPrograms=[0, 0, 0],
            pointsToBuild=3,
            positionsA=[-0.034374999999999996, -0.10312500000000002, -0.1375],
            positionsB=[0.15000000000000002, 0.049999999999999996, 0.0]))

    @patch("malcolm.parts.pmac.pmactrajectorypart.POINTS_PER_BUILD", 4)
    def test_update_step(self):
        task = self.do_configure(axes_to_scan=["x", "y"])
        positionsA = task.put_many.call_args_list[3][0][1]["positionsA"]
        self.assertEqual(len(positionsA), 11)
        self.assertEqual(positionsA[-1], 0.375)
        self.assertEqual(self.o.end_index, 4)
        self.assertEqual(len(self.o.completed_steps_lookup), 11)
        update_completed_steps = MagicMock()
        task = MagicMock()
        self.o.update_step(3, update_completed_steps, task)
        update_completed_steps.assert_called_once_with(1, self.o)
        self.assertEqual(self.o.loading, False)
        self.assertEqual(task.put_many.call_count, 2)
        self.assertEqual(task.post.call_count, 1)
        self.check_resolutions_and_use(task.put_many.call_args_list[0][0][1])
        self.assertEqual(task.post.call_args_list[0],
                         call(self.child["appendProfile"]))
        self.assertEqual(task.put_many.call_args_list[1][0][1], dict(
            timeArray=[
                500000, 500000, 500000, 500000, 100000],
            velocityMode=[
                0, 0, 0, 1, 3],
            userPrograms=[
                4, 3, 4, 2, 8],
            pointsToBuild=5,
            positionsA=[
                0.25, 0.125, 0.0, -0.125, -0.1375],
            positionsB=[
                0.1, 0.1, 0.1, 0.1, 0.1]))

    def test_run(self):
        task = Mock()
        update = Mock()
        self.o.run(task, update)
        task.subscribe.assert_called_once_with(
            self.child["pointsScanned"], self.o.update_step, update, task)
        task.post.assert_called_once_with(self.child["executeProfile"])

    def test_multi_run(self):
        self.do_configure(axes_to_scan=["x"])
        self.assertEqual(self.o.completed_steps_lookup,
                         [0, 0, 1, 1, 2, 2, 3, 3])

        task = self.do_configure(
            axes_to_scan=["x"], completed_steps=3, x_pos=0.6375)
        self.assertEqual(task.put_many.call_count, 2)
        self.assertEqual(task.post.call_count, 1)
        self.check_resolutions_and_use(task.put_many.call_args_list[0][0][1],
                                       useB=False)
        self.assertEqual(task.put_many.call_args_list[1][0][1], dict(
            timeArray=[100000, 500000, 500000, 500000, 500000, 500000, 500000, 100000],
            velocityMode=[2, 0, 0, 0, 0, 0, 1, 3],
            userPrograms=[3, 4, 3, 4, 3, 4, 2, 8],
            pointsToBuild=8,
            positionsA=[0.625, 0.5, 0.375, 0.25, 0.125, 0.0,
                                       -0.125, -0.1375],
        ))

    def test_long_move(self):
        task = self.do_configure(axes_to_scan=["x"], x_pos=-10.1375)
        self.assertEqual(task.put_many.call_args_list[1][0][1], dict(
            timeArray=[
                100000, 3300000, 3300000, 3300000, 100000],
            velocityMode=[
                2, 0, 0, 1, 3],
            userPrograms=[
                0, 0, 0, 0, 0],
            pointsToBuild=5,
            positionsA=[
                -10.087499999999999, -6.7875, -3.4875, -0.1875, -0.1375],
        ))

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
