from .model import Model
from .serializable import deserialize_object
from .alarm import Alarm
from .timestamp import TimeStamp


class AttributeModel(Model):
    """Data Model for an Attribute"""

    endpoints = ["meta", "value", "alarm", "timeStamp"]

    def __init__(self, meta, value=None, alarm=None, timeStamp=None):
        #: The `VMeta` for validating value sets
        self.meta = self.set_meta(meta)
        #: The current value of the attribute
        self.value = self.set_value(value, set_alarm_ts=False)
        #: The `Alarm` status associated with the value
        self.alarm = self.set_alarm(alarm)
        #: The `TimeStamp` that the value was last updated
        self.timeStamp = self.set_timeStamp(timeStamp)

    def set_notifier_path(self, notifier, path):
        super(AttributeModel, self).set_notifier_path(notifier, path)
        self.meta.set_notifier_path(notifier, self.path + ["meta"])

    def set_meta(self, meta):
        """Set the meta VMeta"""
        meta = deserialize_object(meta)
        # Check that the meta attribute_class is ourself
        assert hasattr(meta, "attribute_class"), \
            "Expected meta object, got %r" % meta
        assert isinstance(self, meta.attribute_class), \
            "Meta object needs to be attached to %s, we are a %s" % (
                meta.attribute_class, type(self))
        if hasattr(self, "meta"):
            self.meta.set_notifier_path(None, ())
        meta.set_notifier_path(self.notifier, self.path + ["meta"])
        return self.set_endpoint_data("meta", meta)

    def set_value(self, value, set_alarm_ts=True, alarm=None, ts=None):
        """Set the value"""
        value = self.meta.validate(value)
        if set_alarm_ts:
            if alarm is None:
                alarm = Alarm.ok
            else:
                alarm = deserialize_object(alarm, Alarm)
            if ts is None:
                ts = TimeStamp()
            else:
                ts = deserialize_object(ts, TimeStamp)
            self.set_value_alarm_ts(value, alarm, ts)
        else:
            self.set_endpoint_data("value", value)
        return self.value

    def set_value_alarm_ts(self, value, alarm, ts):
        """Set value with pre-validated alarm and timeStamp"""
        with self.notifier.changes_squashed:
            # Assume they are of the right format
            self.value = value
            self.notifier.add_squashed_change(self.path + ["value"], value)
            self.alarm = alarm
            self.notifier.add_squashed_change(self.path + ["alarm"], alarm)
            self.timeStamp = ts
            self.notifier.add_squashed_change(self.path + ["timeStamp"], ts)

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
