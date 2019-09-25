import pytest
from cothread import cothread
from mock import Mock, call
from malcolm.modules.pmac import VelocityProfile
import matplotlib.pyplot as plt
import numpy as np
import math

from os import environ
import unittest

ASSERT_RESULT = False


class TestPmacStatusPart(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def plot_hat(title, result, expected, show_expected=True):
        fig1 = plt.figure(figsize=(8, 6), dpi=150, frameon=False, num=title)
        if show_expected:
            t, v = make_points(*expected, accumulate=False)
            plt.plot(t, v, color='red', lw=4, alpha=80)
        t, v = make_points(*result)
        plt.plot(t, v)
        plt.show()

    def try_test(self, v1, v2, d, t, a, v_max, title, expected=None):
        title_mode = title
        print(title_mode)
        profile = VelocityProfile(v1, v2, d, t, a, v_max)
        res = profile.get_profile()
        d_res = profile.calc_distance()

        print
        # if the calculated distance matches the requested then all is good
        assert np.isclose(d, d_res), "d {} <> {}".format(d, d_res)

        if environ.get("PLOTS") == '1':
            self.plot_hat(title_mode, res, expected)

    def test_all_zones(self):
        v1 = 4
        v2 = 2
        a = 2
        t = 8
        # the following distances are chosen to place vm in:
        # (a) the lower bound of z1 z2 z3 + upper bound z3
        ds = [7.5, 17, 31, 55.5]
        # (b) the mid points
        ds += [-1.375, 24, 7.5]
        # (d) the intermediate points above mid
        ds += [10.5, 24, 55]
        # (d) the intermediate points below mid
        ds += [-7, 20.5, 32.5]
        for d in ds:
            self.try_test(v1, v2, d, t, a, 1000, "4to2in8over_{}".format(d))
