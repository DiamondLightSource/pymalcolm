import unittest

from scanpointgenerator import Point

from malcolm.modules.pmac.infos import MotorInfo
from malcolm.modules.pmac.util import profile_between_points


class ProfileBetweenPoints(unittest.TestCase):
    def setUp(self):
        # Motor info and axis mappings from P99 sample stages
        self.sample_x_motor_info = MotorInfo(
            "X",
            "BRICK1.CS1",
            18.0,
            -2e-05,
            0.0,
            1.8,
            1.0,
            "sample_x",
            0.0,
            "mm",
            0.0,
            0.0,
            0.0,
            0.0,
        )
        self.sample_y_motor_info = MotorInfo(
            "Y",
            "BRICK1.CS1",
            18.0,
            2e-05,
            0.0,
            1.8,
            1.0,
            "sample_y",
            0.0,
            "mm",
            0.0,
            0.0,
            0.0,
            0.0,
        )
        self.axis_mapping = {
            "sample_x": self.sample_x_motor_info,
            "sample_y": self.sample_y_motor_info,
        }

    def test_approximately_stationary_axis_results_in_2_profile_points(self):
        # The stationary point which causes a problem on P99 testing
        position = {"sample_y": 1.0000000000000888, "sample_x": 1.5}
        point = Point()
        point.lower = position
        point.positions = position
        point.upper = position
        point.duration = 0.1

        next_position = {"sample_y": 1.0000000000000666, "sample_x": 1.0}
        next_point = Point()
        next_point.lower = next_position
        next_point.positions = next_position
        next_point.upper = next_position
        next_point.duration = 0.1

        # Turnaround interval on P99
        min_turnaround = 0.002
        min_interval = 0.002

        time_arrays, velocity_arrays = profile_between_points(
            self.axis_mapping,
            point,
            next_point,
            min_time=min_turnaround,
            min_interval=min_interval,
        )

        expected_time_arrays = {
            "sample_x": [0.0, 0.1, 0.284, 0.384],
            "sample_y": [0.0, 0.384],
        }
        expected_velocity_arrays = {
            "sample_x": [0.0, -1.760563380282, -1.760563380282, 0.0],
            "sample_y": [0, 0],
        }
        self.assertEqual(time_arrays, expected_time_arrays)
        self.assertEqual(velocity_arrays, expected_velocity_arrays)

    def test_stationary_profile_is_two_points(self):
        # Create the two points the same as each other
        position = {"sample_y": 1.0, "sample_x": 1.5}
        point = Point()
        point.lower = position
        point.positions = position
        point.upper = position
        point.duration = 0.1

        # Turnaround interval on P99
        min_turnaround = 0.002
        min_interval = 0.002

        time_arrays, velocity_arrays = profile_between_points(
            self.axis_mapping,
            point,
            point,
            min_time=min_turnaround,
            min_interval=min_interval,
        )

        expected_time_arrays = {
            "sample_x": [0.0, 0.002],
            "sample_y": [0.0, 0.002],
        }
        expected_velocity_arrays = {
            "sample_x": [0.0, 0.0],
            "sample_y": [0.0, 0.0],
        }
        self.assertEqual(time_arrays, expected_time_arrays)
        self.assertEqual(velocity_arrays, expected_velocity_arrays)
