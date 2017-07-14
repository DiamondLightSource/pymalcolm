import numpy as np

from malcolm.compat import str_
from .serializable import Serializable, deserialize_object


def sort_names(d):
    name_d = dict((k, v) for k, v in d.items() if isinstance(v, int))
    return list(sorted(name_d, key=name_d.__getitem__))


class AlarmSeverity(object):
    NO_ALARM, MINOR_ALARM, MAJOR_ALARM, INVALID_ALARM, UNDEFINED_ALARM = \
        range(5)
    names = sort_names(locals())


class AlarmStatus(object):
    NO_STATUS, DEVICE_STATUS, DRIVER_STATUS, RECORD_STATUS, DB_STATUS, \
        CONF_STATUS, UNDEFINED_STATUS, CLIENT_STATUS = range(8)
    names = sort_names(locals())


@Serializable.register_subclass("alarm_t")
class Alarm(Serializable):

    endpoints = ["severity", "status", "message"]
    __slots__ = endpoints

    def __init__(self, severity=AlarmSeverity.NO_ALARM,
                 status=AlarmStatus.NO_STATUS, message=""):
        # Set initial values
        assert int(severity) in range(len(AlarmSeverity.names)), \
            "Expected AlarmSeverity.*_ALARM, got %r" % severity
        self.severity = np.int32(severity)
        assert int(status) in range(len(AlarmStatus.names)), \
            "Expected AlarmStatus.*_STATUS, got %r" % status
        self.status = np.int32(status)
        self.message = deserialize_object(message, str_)

    @classmethod
    def major(cls, message):
        return cls(
            AlarmSeverity.MAJOR_ALARM, AlarmStatus.DEVICE_STATUS, message)

    @classmethod
    def invalid(cls, message):
        return cls(
            AlarmSeverity.INVALID_ALARM, AlarmStatus.DEVICE_STATUS, message)

Alarm.ok = Alarm()