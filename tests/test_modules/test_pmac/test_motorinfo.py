import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

import unittest

from malcolm.infos.pmac import MotorInfo


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