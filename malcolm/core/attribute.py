from .view import View


class Attribute(View):
    """Represents a value with type information that may be backed elsewhere"""

    def __init__(self, controller, context, data):
        self._do_init(controller, context, data)

    @property
    def meta(self):
        return self._controller.make_view(self._context, self._data, "meta")

    @property
    def value(self):
        return self._controller.make_view(self._context, self._data, "value")

    def put_value(self, value, timeout=None):
        """Put a value to the Attribute and wait for completion"""
        self._context.put(self._data.path + ["value"], value, timeout=timeout)

    def put_value_async(self, value):
        fs = self._context.put_async(self._data.path + ["value"], value)
        return fs

    @property
    def alarm(self):
        return self._controller.make_view(self._context, self._data, "alarm")

    @property
    def timeStamp(self):
        return self._controller.make_view(
            self._context, self._data, "timeStamp")

    def __repr__(self):
        return "<%s value=%r>" % (self.__class__.__name__, self.value)
