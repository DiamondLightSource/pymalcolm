from .view import View


class Attribute(View):
    """Represents a value with type information that may be backed elsewhere"""

    def put_value(self, value):
        self._context.put(self._data.path + ["value"], value)

    def put_value_async(self, value):
        fs = self._context.put_async(self._data.path + ["value"], value)
        return fs

    def __setattr__(self, name, value):
        if name == "value":
            self.put_value(value)
        else:
            super(Attribute, self).__setattr__(name, value)
