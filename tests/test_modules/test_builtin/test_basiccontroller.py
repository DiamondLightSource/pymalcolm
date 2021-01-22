import unittest

from malcolm.core import Alarm, AlarmSeverity, Process
from malcolm.modules.builtin.controllers import BasicController
from malcolm.modules.builtin.infos import HealthInfo


class TestBasicController(unittest.TestCase):
    def setUp(self):
        self.process = Process("proc")
        self.o = BasicController("MyMRI")
        self.process.add_controller(self.o)
        self.process.start()
        self.b = self.process.block_view("MyMRI")

    def tearDown(self):
        self.process.stop(timeout=2)

    def update_health(self, num, alarm=Alarm.ok):
        self.o.update_health(num, HealthInfo(alarm))

    def test_set_health(self):
        self.update_health(1, Alarm(severity=AlarmSeverity.MINOR_ALARM))
        self.update_health(2, Alarm(severity=AlarmSeverity.MAJOR_ALARM))
        assert self.b.health.alarm.severity == AlarmSeverity.MAJOR_ALARM

        self.update_health(1, Alarm(severity=AlarmSeverity.UNDEFINED_ALARM))
        self.update_health(2, Alarm(severity=AlarmSeverity.INVALID_ALARM))
        assert self.b.health.alarm.severity == AlarmSeverity.UNDEFINED_ALARM

        self.update_health(1)
        self.update_health(2)
        assert self.o.health.value == "OK"
