from enum import Enum

import numpy as np
from annotypes import Anno, Serializable, deserialize_object


class AlarmSeverity(Enum):
    """An alarm severity"""

    NO_ALARM, MINOR_ALARM, MAJOR_ALARM, INVALID_ALARM, UNDEFINED_ALARM = np.arange(
        5, dtype=np.int32
    )


class AlarmStatus(Enum):
    """An alarm status"""

    (
        NO_STATUS,
        DEVICE_STATUS,
        DRIVER_STATUS,
        RECORD_STATUS,
        DB_STATUS,
        CONF_STATUS,
        UNDEFINED_STATUS,
        CLIENT_STATUS,
    ) = np.arange(8, dtype=np.int32)


with Anno("The alarm severity"):
    AAlarmSeverity = AlarmSeverity
with Anno("The alarm status"):
    AAlarmStatus = AlarmStatus
with Anno("A descriptive alarm message"):
    AMessage = str


@Serializable.register_subclass("alarm_t")
class Alarm(Serializable):
    """Model representing a alarm state with severity, status and message"""

    __slots__ = ["severity", "status", "message"]

    def __init__(
        self,
        severity: AAlarmSeverity = AlarmSeverity.NO_ALARM,
        status: AAlarmStatus = AlarmStatus.NO_STATUS,
        message: AMessage = "",
    ) -> None:
        if not isinstance(severity, AlarmSeverity):
            severity = AlarmSeverity(severity)
        self.severity = severity
        if not isinstance(status, AlarmStatus):
            status = AlarmStatus(status)
        self.status = status
        self.message = deserialize_object(message, str)

    @classmethod
    def major(cls, message: str) -> "Alarm":
        return cls(AlarmSeverity.MAJOR_ALARM, AlarmStatus.DEVICE_STATUS, message)

    @classmethod
    def invalid(cls, message: str) -> "Alarm":
        return cls(AlarmSeverity.INVALID_ALARM, AlarmStatus.DEVICE_STATUS, message)

    @classmethod
    def disconnected(cls, message: str) -> "Alarm":
        return cls(AlarmSeverity.UNDEFINED_ALARM, AlarmStatus.CLIENT_STATUS, message)

    def is_ok(self) -> bool:
        return self.severity == AlarmSeverity.NO_ALARM

    def __ne__(self, other):
        return type(other) != Alarm or other.to_dict() != self.to_dict()

    def __eq__(self, other):
        return not self != other

    ok: "Alarm"  # filled in below


Alarm.ok = Alarm()
