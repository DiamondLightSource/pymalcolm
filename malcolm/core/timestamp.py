import time

from .serializable import Serializable


@Serializable.register_subclass("time_t")
class TimeStamp(Serializable):

    endpoints = ["secondsPastEpoch", "nanoseconds", "userTag"]
    __slots__ = endpoints

    def __init__(self, secondsPastEpoch=None, nanoseconds=None, userTag=0):
        # Set initial values
        if secondsPastEpoch is None or nanoseconds is None:
            now = time.time()
            self.secondsPastEpoch = int(now)
            self.nanoseconds = int(now % 1 / 1e-9)
        else:
            # Assume we have been passed the right types...
            self.secondsPastEpoch = secondsPastEpoch
            self.nanoseconds = nanoseconds
        self.userTag = userTag

    def to_time(self):
        return self.secondsPastEpoch + 1e-9 * self.nanoseconds
