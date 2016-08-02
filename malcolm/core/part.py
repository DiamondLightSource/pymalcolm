from malcolm.core.loggable import Loggable


class Part(Loggable):
    def __init__(self, params, process):
        self.params = params
        self.process = process

    def create_attributes(self):
        raise NotImplementedError()
