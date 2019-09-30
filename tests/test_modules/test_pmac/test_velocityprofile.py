import unittest

import numpy as np

from malcolm.modules.pmac import VelocityProfile


class TestPmacStatusPart(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @staticmethod
    def do_test_distance_range(v1, v2):
        ds = np.arange(-100, 100, 0.5)
        for d in ds:
            profile = VelocityProfile(v1, v2, d, 8.0, 2.0, 10000)
            res = profile.get_profile()
            d_res = profile.calculate_distance()
            assert np.isclose(d_res, d), \
                "Incorrect d returned at d {:03.1f}, vm {:02.03f} " \
                "difference {:02.03f}".format(d, profile.vm, d - d_res)

    @staticmethod
    def do_test_time_range(v1, v2):
        ts = np.arange(.1, 20, .1)
        for t in ts:
            profile = VelocityProfile(v1, v2, 100, t, 2.0, 10000)
            res = profile.get_profile()
            d_res = profile.calculate_distance()
            assert np.isclose(d_res, 100), \
                "Incorrect d returned at d {:03.1f}, vm {:02.03f} " \
                "difference {:02.03f}".format(d, profile.vm, d - d_res)

    def test_all_pos(self):
        self.do_test_distance_range(4.0, 2.0)
        self.do_test_distance_range(400.0, 200.0)
        self.do_test_time_range(4.0, 2.0)

    def test_neg_pos(self):
        self.do_test_distance_range(-2.0, 2.0)
        self.do_test_distance_range(-200.0, 200.0)
        self.do_test_time_range(-2.0, 2.0)

    def test_pos_neg(self):
        self.do_test_distance_range(4.0, -4.0)
        self.do_test_distance_range(400.0, -400.0)
        self.do_test_time_range(4.0, -4.0)

    def test_neg_neg(self):
        self.do_test_distance_range(-4.0, -4.0)
        self.do_test_distance_range(-400.0, -400.0)
        self.do_test_time_range(-4.0, -4.0)
