import unittest

import numpy as np

from malcolm.modules.pmac import VelocityProfile

ASSERT_RESULT = False


class TestPmacStatusPart(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    # def plot_hat(title, result, expected, show_expected=True):
    #     fig1 = plt.figure(figsize=(8, 6), dpi=150, frameon=False, num=title)
    #     if show_expected:
    #         t, v = make_points(*expected, accumulate=False)
    #         plt.plot(t, v, color='red', lw=4, alpha=80)
    #     t, v = make_points(*result)
    #     plt.plot(t, v)
    #     plt.show()

    @staticmethod
    def check_distance(v1, v2, d, t, a, v_max, title, expected=None):
        print(title)
        profile = VelocityProfile(v1, v2, d, t, a, v_max)
        res = profile.get_profile()
        d_res = profile.calc_distance()

        # if the calculated distance matches the requested then all is good
        assert np.isclose(d, d_res), "d {} <> {}".format(d, d_res)

        # if environ.get("PLOTS") == '1':
        #     self.plot_hat(title_mode, res, expected)

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
            d_res = profile.calc_distance()
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
