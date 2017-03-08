import time

import numpy as np

from .serializable import Serializable


@Serializable.register_subclass("time_t")
class TimeStamp(Serializable):

    endpoints = ["secondsPastEpoch", "nanoseconds", "userTag"]

    def __init__(self, secondsPastEpoch=None, nanoseconds=None, userTag=0):
        # Set initial values
        if secondsPastEpoch is None or nanoseconds is None:
            now = time.time()
            secondsPastEpoch = np.int64(now)
            nanoseconds = np.int32(now % 1 / 1e-9)
        self.secondsPastEpoch = np.int64(secondsPastEpoch)
        self.nanoseconds = np.int32(nanoseconds)
        self.userTag = np.int32(userTag)

    def to_time(self):
        return self.secondsPastEpoch + 1e-9 * self.nanoseconds
