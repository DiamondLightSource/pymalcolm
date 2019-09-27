import unittest

import numpy as np

from malcolm.modules.pmac import VelocityProfile

ASSERT_RESULT = False


class TestPmacStatusPart(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @staticmethod
    def do_test_full_range(v1, v2):
        range_profile = VelocityProfile(v1, v2, 1, 8.0, 2.0, 10000)
        range_profile.check_range()
        d = range_profile.d_trough
        print("PEAK", range_profile.d_peak)

        top = range_profile.d_peak
        while d <= top or np.isclose(top, d):
            profile = VelocityProfile(v1, v2, d, 8.0, 2.0, 10000)
            res = profile.get_profile()
            d_res = profile.calculate_distance()
            assert np.isclose(d_res, d), \
                "Incorrect d returned at d {:03.1f}, vm {:02.03f} " \
                "difference {:02.03f}".format(d, profile.vm, d - d_res)

            print("v1 {} v2 {} vm {} d {}".format(v1, v2, profile.vm, d_res))
            d += .1

    def test_all_pos(self):
        self.do_test_full_range(4.0, 2.0)

    def test_neg_pos(self):
        self.do_test_full_range(-2.0, 2.0)

    def test_pos_neg(self):
        self.do_test_full_range(4.0, -4.0)

    def test_neg_neg(self):
        self.do_test_full_range(-4.0, -4.0)

    def test_extend_time(self):
        d = 60.0
        profile = VelocityProfile(40, -35, d, 2.0, 2.0, 200)

        profile.get_profile()
        d_res = profile.calculate_distance()
        assert np.isclose(d_res, d), \
            "Incorrect d returned at d {:03.1f}, vm {:02.03f} " \
            "difference {:02.03f}".format(d, profile.vm, d - d_res)
