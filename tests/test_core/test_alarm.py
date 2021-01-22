import unittest

from malcolm.core.alarm import Alarm, AlarmSeverity, AlarmStatus


class TestAlarm(unittest.TestCase):
    def test_no_alarm(self):
        o = Alarm()
        assert o.severity == AlarmSeverity.NO_ALARM
        assert o.status == AlarmStatus.NO_STATUS
        assert o.message == ""

    def test_names(self):
        assert AlarmStatus.DRIVER_STATUS.name == "DRIVER_STATUS"

    def test_bad_number(self):
        with self.assertRaises(ValueError):
            Alarm(33, 33, "")
