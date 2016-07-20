from malcolm.core.loggable import Loggable


class Part(Loggable):
    def __init__(self, name, process, block, params):
        self.process = process
        self.block = block
        self.name = name
        self.set_logger_name("%s.%s" % (block, name))
        self._call_setup(params)

    def _call_setup(self, params):
        # Expect setup() implementation to be decorated with @takes so it will
        # have a Method attached to it. Calling the Method will fill in defaults
        if not hasattr(self.setup, "Method"):
            raise NotImplementedError()
        # unfortunately thi has to be done now rather than at @takes decorate
        # time so it gets the bound method rather than the unbound function
        self.setup.Method.set_function(self.setup)
        self.setup.Method.call_function(params)

    def setup(selfself, params):
        raise NotImplementedError()
