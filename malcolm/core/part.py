from malcolm.core.loggable import Loggable
from malcolm.core.methodmeta import get_method_decorated


class Part(Loggable):
    def __init__(self, process, params):
        self.process = process
        self.params = params

    def create_methods(self):
        return get_method_decorated(self)

    def create_attributes(self):
        return iter(())
