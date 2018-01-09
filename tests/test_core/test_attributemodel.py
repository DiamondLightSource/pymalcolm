from collections import OrderedDict
import unittest

from malcolm.core import NTScalar
from malcolm.core.alarm import Alarm, AlarmSeverity, AlarmStatus
from malcolm.core.timestamp import TimeStamp
from malcolm.core.vmetas import StringMeta


class TestAttribute(unittest.TestCase):

    def setUp(self):
        self.meta = StringMeta()
        self.o = self.meta.create_attribute_model()

    def test_init(self):
        self.assertIs(self.o.meta, self.meta)
        assert self.o.value == ""
        assert self.o.typeid == "epics:nt/NTScalar:1.0"

    def test_set_value(self):
        value = "test_value"
        self.o.set_value(value)
        assert self.o.value == value

    def test_set_alarm(self):
        alarm = Alarm(
            AlarmSeverity.MAJOR_ALARM, AlarmStatus.DEVICE_STATUS, "bad")
        self.o.set_alarm(alarm)
        assert self.o.alarm == alarm

    def test_set_timeStamp(self):
        timeStamp = TimeStamp()
        self.o.set_ts(timeStamp)
        assert self.o.timeStamp == timeStamp


class TestSerialization(unittest.TestCase):

    def setUp(self):
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "epics:nt/NTScalar:1.0"
        self.serialized["meta"] = StringMeta("desc").to_dict()
        self.serialized["value"] = "some string"
        self.serialized["alarm"] = Alarm().to_dict()
        self.serialized["timeStamp"] = TimeStamp().to_dict()

    def test_to_dict(self):
        a = StringMeta("desc").create_attribute_model()
        a.set_value("some string")
        a.set_ts(self.serialized["timeStamp"])
        assert a.to_dict() == self.serialized

    def test_from_dict(self):
        a = NTScalar.from_dict(self.serialized)
        assert a.meta.to_dict() == StringMeta("desc").to_dict()
        assert a.value == "some string"
