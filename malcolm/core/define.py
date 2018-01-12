from annotypes import WithCallTypes, Anno, Any


with Anno("The name of the defined parameter"):
    AName = str
with Anno("The value of the defined parameter"):
    AValue = Any


class Define(WithCallTypes):
    def __init__(self, name, value):
        # type: (AName, AValue) -> None
        self.name = name
        self.value = value
