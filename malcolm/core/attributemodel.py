from .model import Model
from .serializable import deserialize_object
from .alarm import Alarm
from .timestamp import TimeStamp


class AttributeModel(Model):
    """Data Model for an Attribute"""

    endpoints = ["meta", "value", "alarm", "timeStamp"]

    def __init__(self, meta, value=None, alarm=None, timeStamp=None):
        self.meta = self.set_meta(meta)
        self.value = self.set_value(value)
        self.alarm = self.set_alarm(alarm)
        self.timeStamp = self.set_timeStamp(timeStamp)

    def set_meta(self, meta):
        """Set the meta VMeta"""
        meta = deserialize_object(meta)
        # Check that the meta attribute_class is ourself
        assert hasattr(meta, "attribute_class"), \
            "Expected meta object, got %r" % meta
        assert isinstance(self, meta.attribute_class), \
            "Meta object needs to be attached to %s, we are a %s" % (
                meta.attribute_class, type(self))
        return self.set_endpoint_data("meta", meta)

    def set_value(self, value, set_alarm_ts=True, alarm=None, ts=None):
        """Set the value"""
        value = self.meta.validate(value)
        with self.notifier.changes_squashed:
            self.set_endpoint_data("value", value)
            if set_alarm_ts:
                self.set_alarm(alarm)
                self.set_timeStamp(ts)
        return value

    def set_alarm(self, alarm=None):
        """Set the Alarm"""
        if alarm is None:
            alarm = Alarm.ok
        else:
            alarm = deserialize_object(alarm, Alarm)
        return self.set_endpoint_data("alarm", alarm)

    def set_timeStamp(self, timeStamp=None):
        """Set the TimeStamp"""
        if timeStamp is None:
            timeStamp = TimeStamp()
        else:
            timeStamp = deserialize_object(timeStamp, TimeStamp)
        return self.set_endpoint_data("timeStamp", timeStamp)
