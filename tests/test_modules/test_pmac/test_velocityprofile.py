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
            t = 8
            profile = VelocityProfile(v1, v2, d, t, 2.0, 10000)
            profile.get_profile()
            d_res = profile.calculate_distance()
            assert np.isclose(d_res, d), \
                "Wrong d({}). Expected d {}, vm {}, v1 {}, v2 {}, t {}".format(
                    d_res, d, profile.vm, v1, v2, t)

    @staticmethod
    def do_test_time_range(v1, v2):
        ts = np.arange(.01, 20, .1)
        for t in ts:
            d = 100
            profile = VelocityProfile(v1, v2, d, t, 2.0, 10000)
            profile.get_profile()
            d_res = profile.calculate_distance()
            assert np.isclose(d_res, 100), \
                "Wrong d({}). Expected d {}, vm {}, v1 {}, v2 {}, t {}".format(
                    d_res, d, profile.vm, profile.v1, profile.v2, profile.tv2)

    @staticmethod
    def do_test_v_max_range(v1, v2):
        ms = np.arange(4, 100, 3)
        for v_max in ms:
            d, t = 100, 8
            profile = VelocityProfile(v1, v2, d, t, 2.0, v_max)
            profile.get_profile()
            d_res = profile.calculate_distance()
            assert np.isclose(d_res, 100), \
                "Wrong d({}). Expected d {}, vm {}, v1 {}, v2 {}, t {}".format(
                    d_res, d, profile.vm, profile.v1, profile.v2, profile.tv2)

    def test_pos_pos(self):
        self.do_test_distance_range(4.0, 2.0)
        self.do_test_distance_range(400.0, 200.0)
        self.do_test_time_range(4.0, 2.0)
        self.do_test_v_max_range(4.0, 2.0)

    def test_neg_pos(self):
        self.do_test_distance_range(-2.0, 2.0)
        self.do_test_distance_range(-200.0, 200.0)
        self.do_test_time_range(-2.0, 2.0)
        self.do_test_v_max_range(-2.0, 2.0)

    def test_pos_neg(self):
        self.do_test_distance_range(4.0, -4.0)
        self.do_test_distance_range(400.0, -400.0)
        self.do_test_time_range(4.0, -4.0)
        self.do_test_v_max_range(4.0, -4.0)

    def test_neg_neg(self):
        self.do_test_distance_range(-4.0, -4.0)
        self.do_test_distance_range(-400.0, -400.0)
        self.do_test_time_range(-4.0, -4.0)
        self.do_test_v_max_range(-4.0, -4.0)

    def ____test_check_one(self):
        d = -1.5
        profile = VelocityProfile(
            v1=400.0, v2=-400.0, d=d, tv2=8.0, a=2.0, v_max=1000
        )
        profile.get_profile()
        d_res = profile.calculate_distance()
        assert np.isclose(d_res, d), \
            "Wrong d({}). Expected d {}, vm {}, v1 {}, v2 {}, t {}".format(
                d_res, d, profile.vm, profile.v1, profile.v2, profile.tv2)