import time

import numpy as np
from annotypes import Anno, Serializable, TYPE_CHECKING

from malcolm.compat import InsertionOrderedDict

if TYPE_CHECKING:
    from typing import Type, Dict, Any


with Anno("Seconds since Jan 1, 1970 00:00:00 UTC"):
    ASecondsPastEpoch = np.int64
with Anno("Nanoseconds relative to the secondsPastEpoch field"):
    ANanoseconds = np.int32
with Anno("An integer value whose interpretation is deliberately undefined"):
    AUserTag = np.int32


zero32 = np.int32(0)


# Make a fixed serialized
class TimeStampOrderedDict(InsertionOrderedDict):
    # Fix them as a tuple as they never change. This will make pop etc. fail
    _keys = ("typeid", "secondsPastEpoch", "nanoseconds", "userTag")

    def __init__(self, secondsPastEpoch, nanoseconds, userTag):
        # Don't call superclass as it would overwrite _keys
        dict.__init__(self,
                      typeid="time_t",
                      secondsPastEpoch=secondsPastEpoch,
                      nanoseconds=nanoseconds,
                      userTag=userTag)


@Serializable.register_subclass("time_t")
class TimeStamp(Serializable):

    __slots__ = ["secondsPastEpoch", "nanoseconds", "userTag"]

    # noinspection PyPep8Naming
    # secondsPastEpoch and userTag are camelCase to maintain compatibility with
    # EPICS normative types
    def __init__(self, secondsPastEpoch=None, nanoseconds=None, userTag=zero32):
        # type: (ASecondsPastEpoch, ANanoseconds, AUserTag) -> None
        # Set initial values
        if secondsPastEpoch is None or nanoseconds is None:
            now = time.time()
            self.secondsPastEpoch = np.int64(now)
            self.nanoseconds = np.int32(now % 1 / 1e-9)
        else:
            self.secondsPastEpoch = np.int64(secondsPastEpoch)
            self.nanoseconds = np.int32(nanoseconds)
        self.userTag = userTag

    def to_time(self):
        # type: () -> float
        return self.secondsPastEpoch + 1e-9 * self.nanoseconds

    def to_dict(self, dict_cls=TimeStampOrderedDict):
        # type: (Type[dict]) -> Dict[str, Any]
        # This needs to be fast as we do it a lot, so use a plain dict instead
        # of an OrderedDict
        return TimeStampOrderedDict(
            secondsPastEpoch=self.secondsPastEpoch,
            nanoseconds=self.nanoseconds,
            userTag=self.userTag
        )

    zero = None  # filled in below


TimeStamp.zero = TimeStamp(0, zero32)

