from malcolm.core.loggable import Loggable
from malcolm.core.serializable import Serializable
from malcolm.core.method import get_method_decorated


class Part(Loggable):
    def __init__(self, params, process):
        self.params = params
        self.process = process

    def create_attributes(self):
        raise NotImplementedError()
