from collections import OrderedDict
import unittest

from malcolm.core.ntscalar import NTScalar
from malcolm.core.alarm import Alarm, AlarmSeverity, AlarmStatus
from malcolm.core.timestamp import TimeStamp
from malcolm.modules.builtin.vmetas import StringMeta


class TestAttribute(unittest.TestCase):

    def setUp(self):
        self.meta = StringMeta()
        self.o = self.meta.create_attribute()

    def test_init(self):
        self.assertIs(self.o.meta, self.meta)
        self.assertEquals(self.o.value, "")
        self.assertEquals(self.o.typeid, "epics:nt/NTScalar:1.0")

    def test_set_value(self):
        value = "test_value"
        self.o.set_value(value)
        self.assertEquals(self.o.value, value)

    def test_set_alarm(self):
        alarm = Alarm(
            AlarmSeverity.MAJOR_ALARM, AlarmStatus.DEVICE_STATUS, "bad")
        self.o.set_alarm(alarm)
        self.assertEquals(self.o.alarm, alarm)

    def test_set_timeStamp(self):
        timeStamp = TimeStamp()
        self.o.set_timeStamp(timeStamp)
        self.assertEquals(self.o.timeStamp, timeStamp)


class TestSerialization(unittest.TestCase):

    def setUp(self):
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "epics:nt/NTScalar:1.0"
        self.serialized["meta"] = StringMeta("desc").to_dict()
        self.serialized["value"] = "some string"
        self.serialized["alarm"] = Alarm().to_dict()
        self.serialized["timeStamp"] = TimeStamp().to_dict()

    def test_to_dict(self):
        a = StringMeta("desc").create_attribute()
        a.set_value("some string")
        a.set_timeStamp(self.serialized["timeStamp"])
        self.assertEqual(a.to_dict(), self.serialized)

    def test_from_dict(self):
        a = NTScalar.from_dict(self.serialized)
        self.assertEquals(a.meta.to_dict(), StringMeta("desc").to_dict())
        self.assertEquals(a.value, "some string")
