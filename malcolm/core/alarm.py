from enum import Enum

import numpy as np
from annotypes import Anno

from malcolm.compat import str_
from .serializable import Serializable, deserialize_object


class AlarmSeverity(Enum):
    NO_ALARM, MINOR_ALARM, MAJOR_ALARM, INVALID_ALARM, UNDEFINED_ALARM = \
        np.arange(5, dtype=np.int32)


class AlarmStatus(Enum):
    NO_STATUS, DEVICE_STATUS, DRIVER_STATUS, RECORD_STATUS, DB_STATUS, \
        CONF_STATUS, UNDEFINED_STATUS, CLIENT_STATUS = \
        np.arange(8, dtype=np.int32)


with Anno("The alarm severity"):
    AAlarmSeverity = AlarmSeverity
with Anno("The alarm status"):
    AAlarmStatus = AlarmStatus
with Anno("A descriptive alarm message"):
    AMessage = str


@Serializable.register_subclass("alarm_t")
class Alarm(Serializable):

    __slots__ = ["severity", "status", "message"]

    def __init__(self,
                 severity=AlarmSeverity.NO_ALARM,  # type: AAlarmSeverity
                 status=AlarmStatus.NO_STATUS,  # type: AAlarmStatus
                 message="",  # type: AMessage
                 ):
        # type: (...) -> None
        assert isinstance(severity, AlarmSeverity), \
            "Expected AlarmSeverity.*_ALARM, got %r" % severity
        self.severity = severity
        assert isinstance(status, AlarmStatus), \
            "Expected AlarmStatus.*_STATUS, got %r" % status
        self.status = status
        self.message = deserialize_object(message, str_)

    @classmethod
    def major(cls, message):
        # type: (str) -> Alarm
        return cls(
            AlarmSeverity.MAJOR_ALARM, AlarmStatus.DEVICE_STATUS, message)

    @classmethod
    def invalid(cls, message):
        # type: (str) -> Alarm
        return cls(
            AlarmSeverity.INVALID_ALARM, AlarmStatus.DEVICE_STATUS, message)

    def is_ok(self):
        # type: () -> bool
        return self.severity == AlarmSeverity.NO_ALARM


Alarm.ok = Alarm()
