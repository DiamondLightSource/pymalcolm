from enum import Enum

from annotypes import Anno, WithCallTypes


class Status(Enum):
    good, bad, ugly = range(3)


with Anno("The status"):
    AStatus = Status


class EnumTaker(WithCallTypes):
    def __init__(self, status):
        # type: (AStatus) -> None
        if status != Status.good:
            raise ValueError(status)
        else:
            self.status = status
