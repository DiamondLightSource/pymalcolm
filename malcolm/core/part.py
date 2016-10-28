from malcolm.core.methodmeta import get_method_decorated, REQUIRED, method_takes
from malcolm.core.vmetas import StringMeta
from malcolm.core.loggable import Loggable
from malcolm.core.hook import get_hook_decorated


@method_takes(
    "name", StringMeta("Name of the part within controller"), REQUIRED)
class Part(Loggable):
    params = None

    def __init__(self, process, params):
        self.process = process
        self.name = params.name
        self.store_params(params)
        self.method_metas = {}

    def store_params(self, params):
        self.params = params

    def create_methods(self):
        hooked = [name for (name, _, _) in get_hook_decorated(self)]
        for name, method_meta, func in get_method_decorated(self):
            self.method_metas[name] = method_meta
            if name not in hooked:
                yield name, method_meta, func

    def create_attributes(self):
        return iter(())
