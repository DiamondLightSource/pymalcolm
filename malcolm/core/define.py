from typing import Any

from annotypes import Anno, WithCallTypes

with Anno("The name of the defined parameter"):
    AName = str
with Anno("The value of the defined parameter"):
    AValue = Any


class Define(WithCallTypes):
    def __init__(self, name: AName, value: AValue) -> None:
        self.name = name
        self.value = value
