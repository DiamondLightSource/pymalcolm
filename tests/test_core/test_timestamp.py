import time
import unittest

from malcolm.core.timestamp import TimeStamp


class TestAlarm(unittest.TestCase):
    def test_no_args(self):
        now = time.time()
        o = TimeStamp()
        self.assertAlmostEqual(now, o.to_time(), delta=0.2)

    def test_args(self):
        o = TimeStamp(1231112, 211255265, 43)
        assert o.secondsPastEpoch == 1231112
        assert o.nanoseconds == 211255265
        assert o.userTag == 43
        assert o.to_time() == 1231112.211255265
