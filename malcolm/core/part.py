from annotypes import WithCallTypes, Anno

from .loggable import Loggable
from .registrar import Registrar


with Anno("The name of the Part within the Controller"):
    AName = str


class Part(Loggable, WithCallTypes):
    name = None  # type: str

    def __init__(self, name):
        # type: (AName) -> None
        super(Part, self).__init__(name=name)
        self.name = name

    def setup(self, registrar):
        # type: (Registrar) -> None
        """Use the given Registrar to populate the hooks and fields"""
        raise NotImplementedError()
