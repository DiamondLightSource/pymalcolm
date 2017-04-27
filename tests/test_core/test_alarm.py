import unittest

from malcolm.core.alarm import Alarm, AlarmSeverity, AlarmStatus


class TestAlarm(unittest.TestCase):

    def test_no_alarm(self):
        o = Alarm()
        self.assertEqual(o.severity, AlarmSeverity.NO_ALARM)
        self.assertEqual(o.status, AlarmStatus.NO_STATUS)
        self.assertEqual(o.message, "")

    def test_names(self):
        self.assertEqual(AlarmStatus.names[2], "DRIVER_STATUS")

    def test_bad_number(self):
        with self.assertRaises(AssertionError):
            Alarm(33, 33, "")
