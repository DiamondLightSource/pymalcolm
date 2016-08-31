from malcolm.core.methodmeta import get_method_decorated
from malcolm.core.loggable import Loggable
from malcolm.core.hook import get_hook_decorated


class Part(Loggable):
    params = None

    def __init__(self, process, params=None):
        self.process = process
        self.store_params(params)

    def store_params(self, params):
        self.params = params

    def create_methods(self):
        hooked = [name for (name, _, _) in get_hook_decorated(self)]
        for name, method_meta, func in get_method_decorated(self):
            if name not in hooked:
                yield name, method_meta, func

    def create_attributes(self):
        return iter(())
