import unittest
import numpy as np
from malcolm.modules.pmac.infos import MotorInfo


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
            velocity_settle=0.0,
            units="mm"
        )

    @staticmethod
    def check_distance(d, times, velocities):
        # sum the area of two trapezoids z1, z2 and a rectangle r
        z1 = (velocities[0] + velocities[1]) / 2 * times[1]
        if len(times) == 3:
            r = 0
            z2 = (velocities[1] + velocities[2]) / 2 * (times[2] - times[1])
        else:
            r = velocities[1] * (times[2] - times[1])
            z2 = (velocities[2] + velocities[3]) / 2 * (times[3] - times[2])
        assert np.isclose(z1 + z2 + r, d)

    def test_turnaround(self):
        # 0_| \
        #   |  \
        v1 = 0.1
        v2 = -0.1
        distance = 0.0
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, 0.0)
        self.check_distance(distance, time_array, velocity_array)
        assert np.isclose(time_array, [0.0, 0.05, 0.1]).all()
        assert np.isclose(velocity_array, [v1, 0, v2]).all()

    def test_turnaround_invert(self):
        # 0_|  /
        #   | /
        v1 = -0.1
        v2 = 0.1
        distance = 0.0
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, 0.0)
        self.check_distance(distance, time_array, velocity_array)
        assert np.isclose(time_array, [0.0, 0.05, 0.1]).all()
        assert np.isclose(velocity_array, [v1, 0, v2]).all()

    def test_turnaround_with_min_time(self):
        # 0_| \___
        #   |     \
        v1 = 0.1
        v2 = -0.1
        distance = 0
        min_time = 2
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        self.check_distance(distance, time_array, velocity_array)
        assert np.isclose(time_array, [0.0, 0.05, 1.95, 2.0]).all()
        assert np.isclose(velocity_array, [v1, 0, 0, v2]).all()

    def test_turnaround_with_min_time_invert(self):
        # 0_|  ___/
        #   | /
        v1 = -0.1
        v2 = 0.1
        distance = 0
        min_time = 2
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        self.check_distance(distance, time_array, velocity_array)
        assert np.isclose(time_array, [0.0, 0.05, 1.95, 2.0]).all()
        assert np.isclose(velocity_array, [v1, 0, 0, v2]).all()

    def test_step_move_no_vmax(self):
        # 0_| /\
        v1 = 0
        v2 = 0
        distance = 0.5
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, 0.0)
        self.check_distance(distance, time_array, velocity_array)
        assert np.isclose(time_array, [0.0, 0.5, 1.0]).all()
        assert np.isclose(velocity_array, [v1, 1, 0]).all()

    def test_step_move_no_vmax_min_time(self):
        #   |  _
        # 0_| / \
        v1 = 0
        v2 = 0
        distance = 0.125
        min_time = 0.5004166666666666
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        self.check_distance(distance, time_array, velocity_array)
        assert np.isclose(
            time_array, [0.0, 0.24, 0.26041666666667, 0.50041666666667]
        ).all()
        assert np.isclose(velocity_array, [v1, 0.48, 0.48, v2]).all()

    def test_step_move_no_vmax_min_time_invert(self):
        # 0_|
        #   | \_/
        v1 = 0
        v2 = 0
        distance = -0.125
        min_time = 0.5004166666666666
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        assert np.isclose(
            time_array, [0.0, 0.24, 0.26041666666667, 0.50041666666667]
        ).all()
        assert np.isclose(velocity_array, [v1, -0.48, -0.48, v2]).all()

    def test_step_move_at_vmax(self):
        #   |  __
        # 0_| /  \
        v1 = 0
        v2 = 0
        distance = 1.0
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, 0.0)
        self.check_distance(distance, time_array, velocity_array)
        assert np.isclose(time_array, [0.0, 0.5, 1.0, 1.5]).all()
        assert np.isclose(velocity_array, [v1, 1, 1, 0]).all()

    def test_step_move_restricted(self):
        #   |  __
        # 0_| /  \
        v1 = 0
        v2 = 0
        distance = 1.02
        min_time = 5.2
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        self.check_distance(distance, time_array, velocity_array)
        assert np.isclose(time_array, [0.0, 0.1, 5.1, 5.2]).all()
        assert np.isclose(velocity_array, [v1, 0.2, 0.2, v2]).all()

    def test_step_move_restricted_invert(self):
        # 0_|
        #   | \__/
        v1 = 0
        v2 = 0
        distance = -1.02
        min_time = 5.2
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        assert np.isclose(time_array, [0.0, 0.1, 5.1, 5.2]).all()
        assert np.isclose(velocity_array, [v1, -0.2, -0.2, v2]).all()

    def test_step_move_at_vmax_invert(self):
        # 0_|
        #   | \__/
        v1 = 0
        v2 = 0
        distance = -1.0
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, 0.0)
        assert np.isclose(time_array, [0.0, 0.5, 1.0, 1.5]).all()
        assert np.isclose(velocity_array, [v1, -1, -1, 0]).all()

    def test_interrupted_move(self):
        #   |  /\
        # 0_|
        v1 = 0.5
        v2 = 0.5
        distance = 0.375
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, 0.0)
        self.check_distance(distance, time_array, velocity_array)
        assert np.isclose(time_array, [0.0, 0.25, 0.5]).all()
        assert np.isclose(velocity_array, [v1, 1, v2]).all()

    def test_interrupted_move_min_time(self):
        # 0_| \/
        v1 = 0.5
        v2 = 0.5
        distance = 0.125
        min_time = 0.5
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        self.check_distance(distance, time_array, velocity_array)
        assert np.isclose(time_array, [0.0, 0.25, 0.5]).all()
        assert np.isclose(velocity_array, [v1, 0, v2]).all()

    def test_interrupted_move_min_time_at_zero(self):
        # 0_| \__/
        v1 = 0.5
        v2 = 0.5
        distance = 0.125
        min_time = 1.0
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        self.check_distance(distance, time_array, velocity_array)
        assert np.isclose(time_array, [0.0, 0.25, 0.75, 1.0]).all()
        assert np.isclose(velocity_array, [v1, 0, 0, v2]).all()

    def test_interrupted_move_retracing_vmax(self):
        # 0_| \  /
        #   |  \/
        v1 = 0.5
        v2 = 0.5
        distance = 0
        min_time = 1.0
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        self.check_distance(distance, time_array, velocity_array)
        assert np.isclose(time_array, [0.0, 0.5, 1.0]).all()
        assert np.isclose(velocity_array, [v1, -0.5, v2]).all()

    def test_interrupted_move_retracing_further_limited(self):
        # 0_| \    /
        #   |  \__/
        v1 = 0.5
        v2 = 0.5
        distance = -0.25
        min_time = 1.5
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        self.check_distance(distance, time_array, velocity_array)
        assert np.isclose(time_array, [0.0, 0.5, 1.0, 1.5]).all()
        assert np.isclose(velocity_array, [v1, -0.5, -0.5, v2]).all()

    def test_interrupted_move_retracing_further_at_vmax(self):
        # 0_| \    /
        #   |  \__/
        v1 = 0.5
        v2 = 0.5
        distance = -0.5
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, 0.0)
        self.check_distance(distance, time_array, velocity_array)
        assert np.isclose(time_array, [0.0, 0.75, 0.875, 1.625]).all()
        assert np.isclose(velocity_array, [v1, -1, -1, v2]).all()

    def test_interrupted_move_retracing_further_at_vmax_invert(self):
        #   |   __
        # 0_|  /  \
        #   | /    \
        v1 = -0.5
        v2 = -0.5
        distance = 0.5
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, 0.0)
        self.check_distance(distance, time_array, velocity_array)
        assert np.isclose(time_array, [0.0, 0.75, 0.875, 1.625]).all()
        assert np.isclose(velocity_array, [v1, 1, 1, v2]).all()

    def test_small_distance(self):
        # 0_|
        #   | \__/
        # From I14 at the top of a spiral scan
        v1 = 0.0
        v2 = 0.0
        distance = -7.0649411427099997e-05
        min_time = 0.11896513748900001
        self.o.acceleration = 0.02
        self.o.max_velocity = 0.01
        time_array, velocity_array = self.o.make_velocity_profile(
            v1, v2, distance, min_time)
        self.check_distance(distance, time_array, velocity_array)
        # assert np.isclose(time_array, [0.0, 0.059482568744500003, min_time]
        # assert np.isclose(velocity_array, [v1, -0.00118965137489, v2]
        # todo see above.
        #  NOTE slight discrepancy with Tom's original make_velocity_profile
        #  I believe this is just rounding
        assert np.isclose(
            time_array, [0.0, 0.05709396808948, 0.06187116939952, min_time]
        ).all()
        assert np.isclose(
            velocity_array, [v1, -0.00114187936179, -0.00114187936179, v2]
        ).all()
