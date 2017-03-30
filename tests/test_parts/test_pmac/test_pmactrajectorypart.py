import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, call, patch

Mock = MagicMock

from malcolm.parts.pmac.pmactrajectorypart import PMACTrajectoryPart, MotorInfo
from scanpointgenerator import LineGenerator, CompoundGenerator


class TestMotorPVT(unittest.TestCase):
    def setUp(self):
        self.o = MotorInfo(
            cs_axis="X",
            cs_port="BRICK1CS2",
            acceleration=2.0,  # mm/s/s
            resolution=0.001,
            offset=0.0,
            max_velocity=1,
            current_position=32.0,
            scannable="t1x",
            velocity_settle=0.0
        )

    def test_turnaround(self):
        # 0_| \
        #   |  \
        v1 = 0.1
        v2 = -0.1
        distance = 0.0
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, 0.0)
        self.assertEqual(time_array, [0.0, 0.05, 0.1])
        self.assertEqual(velocity_array, [v1, 0, v2])

    def test_turnaround_invert(self):
        # 0_|  /
        #   | /
        v1 = -0.1
        v2 = 0.1
        distance = 0.0
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, 0.0)
        self.assertEqual(time_array, [0.0, 0.05, 0.1])
        self.assertEqual(velocity_array, [v1, 0, v2])

    def test_turnaround_with_min_time(self):
        # 0_| \___
        #   |     \
        v1 = 0.1
        v2 = -0.1
        distance = 0
        min_time = 2
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        self.assertEqual(time_array, [0.0, 0.05, 1.95, 2.0])
        self.assertEqual(velocity_array, [v1, 0, 0, v2])

    def test_turnaround_with_min_time_invert(self):
        # 0_|  ___/
        #   | /
        v1 = -0.1
        v2 = 0.1
        distance = 0
        min_time = 2
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        self.assertEqual(time_array, [0.0, 0.05, 1.95, 2.0])
        self.assertEqual(velocity_array, [v1, 0, 0, v2])

    def test_step_move_no_vmax(self):
        # 0_| /\
        v1 = 0
        v2 = 0
        distance = 0.5
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, 0.0)
        self.assertEqual(time_array, [0.0, 0.5, 1.0])
        self.assertEqual(velocity_array, [v1, 1, 0])

    def test_step_move_no_vmax_min_time(self):
        #   |  _
        # 0_| / \
        v1 = 0
        v2 = 0
        distance = 0.125
        min_time = 0.5004166666666666
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        self.assertEqual(time_array, [0.0, 0.24000000000000069, 0.26041666666666596, 0.50041666666666662])
        self.assertEqual(velocity_array, [v1, 0.48000000000000137, 0.48000000000000137, v2])

    def test_step_move_no_vmax_min_time_invert(self):
        # 0_|
        #   | \_/
        v1 = 0
        v2 = 0
        distance = -0.125
        min_time = 0.5004166666666666
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        self.assertEqual(time_array, [0.0, 0.24000000000000069, 0.26041666666666596, 0.50041666666666662])
        self.assertEqual(velocity_array, [v1, -0.48000000000000137, -0.48000000000000137, v2])

    def test_step_move_at_vmax(self):
        #   |  __
        # 0_| /  \
        v1 = 0
        v2 = 0
        distance = 1.0
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, 0.0)
        self.assertEqual(time_array, [0.0, 0.5, 1.0, 1.5])
        self.assertEqual(velocity_array, [v1, 1, 1, 0])

    def test_step_move_restricted(self):
        #   |  __
        # 0_| /  \
        v1 = 0
        v2 = 0
        distance = 1.02
        min_time = 5.2
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        self.assertEqual(time_array, [0.0, 0.10000000000000009, 5.0999999999999996, 5.1999999999999993])
        self.assertEqual(velocity_array, [v1, 0.20000000000000018, 0.20000000000000018, v2])

    def test_step_move_restricted_invert(self):
        # 0_|
        #   | \__/
        v1 = 0
        v2 = 0
        distance = -1.02
        min_time = 5.2
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        self.assertEqual(time_array, [0.0, 0.10000000000000009, 5.0999999999999996, 5.1999999999999993])
        self.assertEqual(velocity_array, [v1, -0.20000000000000018, -0.20000000000000018, v2])

    def test_step_move_at_vmax_invert(self):
        # 0_|
        #   | \__/
        v1 = 0
        v2 = 0
        distance = -1.0
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, 0.0)
        self.assertEqual(time_array, [0.0, 0.5, 1.0, 1.5])
        self.assertEqual(velocity_array, [v1, -1, -1, 0])

    def test_interrupted_move(self):
        #   |  /\
        # 0_|
        v1 = 0.5
        v2 = 0.5
        distance = 0.375
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, 0.0)
        self.assertEqual(time_array, [0.0, 0.25, 0.5])
        self.assertEqual(velocity_array, [v1, 1, v2])

    def test_interrupted_move_min_time(self):
        # 0_| \/
        v1 = 0.5
        v2 = 0.5
        distance = 0.125
        min_time = 0.5
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        self.assertEqual(time_array, [0.0, 0.25, 0.5])
        self.assertEqual(velocity_array, [v1, 0, v2])

    def test_interrupted_move_min_time_at_zero(self):
        # 0_| \__/
        v1 = 0.5
        v2 = 0.5
        distance = 0.125
        min_time = 1.0
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        self.assertEqual(time_array, [0.0, 0.25, 0.75, 1.0])
        self.assertEqual(velocity_array, [v1, 0, 0, v2])

    def test_interrupted_move_retracing_vmax(self):
        # 0_| \  /
        #   |  \/
        v1 = 0.5
        v2 = 0.5
        distance = 0
        min_time = 1.0
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        self.assertEqual(time_array, [0.0, 0.25, 0.5, 0.75, 1.0])
        self.assertEqual(velocity_array, [v1, 0, -0.5, 0, v2])

    def test_interrupted_move_retracing_further_limited(self):
        # 0_| \    /
        #   |  \__/
        v1 = 0.5
        v2 = 0.5
        distance = -0.25
        min_time = 1.5
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        self.assertEqual(time_array, [0.0, 0.25, 0.5, 1.0, 1.25, 1.5])
        self.assertEqual(velocity_array, [v1, 0, -0.5, -0.5, 0, v2])

    def test_interrupted_move_retracing_further_at_vmax(self):
        # 0_| \    /
        #   |  \__/
        v1 = 0.5
        v2 = 0.5
        distance = -0.5
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, 0.0)
        self.assertEqual(time_array, [0.0, 0.25, 0.75, 0.875, 1.375, 1.625])
        self.assertEqual(velocity_array, [v1, 0, -1, -1, 0, v2])

    def test_interrupted_move_retracing_further_at_vmax_invert(self):
        #   |   __
        # 0_|  /  \
        #   | /    \
        v1 = -0.5
        v2 = -0.5
        distance = 0.5
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, 0.0)
        self.assertEqual(time_array, [0.0, 0.25, 0.75, 0.875, 1.375, 1.625])
        self.assertEqual(velocity_array, [v1, 0, 1, 1, 0, v2])


class TestPMACTrajectoryPart(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.process = Mock()
        self.child = Mock()

        def getitem(name):
            return name

        self.child.__getitem__.side_effect = getitem
        self.child.i10 = 1705244
        self.params = PMACTrajectoryPart.MethodMeta.prepare_input_map(
            name="pmac", mri="TST-PMAC"
        )
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
                acceleration=2.5,
                resolution=0.001,
                offset=0,
                max_velocity=1.0,
                current_position=x_pos,
                scannable="x",
                velocity_settle=0.0,
            )],
            ypart=[MotorInfo(
                cs_axis="B",
                cs_port="CS1",
                acceleration=2.5,
                resolution=0.001,
                offset=0,
                max_velocity=1.0,
                current_position=y_pos,
                scannable="y",
                velocity_settle=0.0,
            )]
        )
        return part_info

    def do_configure(self, axes_to_scan, completed_steps=0, x_pos=0.5,
                     y_pos=0.0, duration=1.0):
        part_info = self.make_part_info(x_pos, y_pos)
        task = Mock()
        steps_to_do = 3 * len(axes_to_scan)
        params = Mock()
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        params.generator = CompoundGenerator([ys, xs], [], [], duration)
        params.generator.prepare()
        params.axesToMove = axes_to_scan
        self.o.configure(task, completed_steps, steps_to_do, part_info, params)
        return task

    def test_validate(self):
        params = Mock()
        params.generator = CompoundGenerator([], [], [], 0.0102)
        params.axesToMove = ["x"]
        part_info = self.make_part_info()
        ret = self.o.validate(None, part_info, params)
        expected = 0.010166
        self.assertEqual(ret[0].value.duration, expected)

    @patch("malcolm.parts.pmac.pmactrajectorypart.INTERPOLATE_INTERVAL", 0.2)
    def test_configure(self):
        task = self.do_configure(axes_to_scan=["x", "y"])
        self.assertEqual(task.put_many.call_count, 4)
        self.assertEqual(task.post.call_count, 2)
        self.assertEqual(task.post_async.call_count, 1)
        self.assertEqual(task.put.call_count, 2)
        self.assertEqual(task.put.call_args_list[0],
                         call(self.child["numPoints"], 4000000))
        self.assertEqual(task.put.call_args_list[1],
                         call(self.child["cs"], "CS1"))
        self.check_resolutions_and_use(task.put_many.call_args_list[0][0][1])
        self.assertEqual(task.put_many.call_args_list[1][0][1], dict(
            timeArray=[207500]*5,
            velocityMode=[0, 0, 0, 0, 2],
            userPrograms=[8]*5,
            pointsToBuild=5,
            positionsA=[0.44617968749999998,
                        0.28499999999999998,
                        0.077499999999999958,
                        -0.083679687500000072,
                        -0.13750000000000007],
            positionsB=[0.0, 0.0, 0.0, 0.0, 0.0]))
        self.assertEqual(task.post.call_args_list[0],
                         call(self.child["buildProfile"]))
        self.assertEqual(task.post_async.call_args_list[0],
                         call(self.child["executeProfile"]))
        self.assertEqual(task.post.call_args_list[1],
                         call(self.child["buildProfile"]))
        self.check_resolutions_and_use(task.put_many.call_args_list[2][0][1])
        self.assertEqual(task.put_many.call_args_list[3][0][1], dict(
            timeArray=[
                100000, 500000, 500000, 500000, 500000, 500000, 500000, 200000,
                200000, 500000, 500000, 500000, 500000, 500000, 500000, 100000],
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

    @patch("malcolm.parts.pmac.pmactrajectorypart.INTERPOLATE_INTERVAL", 0.2)
    def test_2_axis_move_to_start(self):
        task = self.do_configure(axes_to_scan=["x", "y"], x_pos=0.0, y_pos=0.2)
        self.assertEqual(task.put_many.call_count, 4)
        self.assertEqual(task.post.call_count, 2)
        self.assertEqual(task.post_async.call_count, 1)
        self.check_resolutions_and_use(task.put_many.call_args_list[0][0][1])
        self.assertEqual(task.put_many.call_args_list[1][0][1], dict(
            timeArray=[282843, 282842],
            velocityMode=[0, 2],
            userPrograms=[8, 8],
            pointsToBuild=2,
            positionsA=[-0.068750000000000019, -0.13750000000000001],
            positionsB=[0.10000000000000001, 0.0]))

    @patch("malcolm.parts.pmac.pmactrajectorypart.POINTS_PER_BUILD", 4)
    @patch("malcolm.parts.pmac.pmactrajectorypart.INTERPOLATE_INTERVAL", 0.2)
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

    @patch("malcolm.parts.pmac.pmactrajectorypart.INTERPOLATE_INTERVAL", 0.2)
    def test_long_steps_lookup(self):
        task = self.do_configure(
            axes_to_scan=["x"], completed_steps=3, x_pos=0.62506, duration=14.0)
        self.assertEqual(task.put_many.call_args_list[1][0][1], dict(
            timeArray=[7143, 3500000,
                       3500000, 3500000,
                       3500000, 3500000,
                       3500000, 3500000,
                       3500000, 3500000,
                       3500000, 3500000,
                       3500000, 7143],
            velocityMode=[2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 3],
            userPrograms=[3, 0, 4, 0, 3, 0, 4, 0, 3, 0, 4, 0, 2, 8],
            pointsToBuild=14,
            positionsA=[0.625,
                        0.5625,
                        0.5,
                        0.4375,
                        0.375,
                        0.3125,
                        0.25,
                        0.1875,
                        0.125,
                        0.0625,
                        0.0,
                        -0.0625,
                        -0.125,
                        -0.1250637755102041],
        ))
        self.assertEqual(self.o.completed_steps_lookup,
                         [3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6])


    @patch("malcolm.parts.pmac.pmactrajectorypart.INTERPOLATE_INTERVAL", 2.0)
    def test_long_move(self):
        task = self.do_configure(axes_to_scan=["x"], x_pos=-10.1375)
        self.assertEqual(task.put_many.call_args_list[1][0][1], dict(
            timeArray=[2080000, 2080000, 2080000, 2080000, 2080000],
            velocityMode=[0, 0, 0, 0, 2],
            userPrograms=[8, 8, 8, 8, 8],
            pointsToBuild=5,
            positionsA=[-8.2575,
                        -6.177499999999998,
                        -4.097499999999998,
                        -2.0174999999999983,
                        -0.1374999999999984],
        ))


if __name__ == "__main__":
    unittest.main(verbosity=2)
