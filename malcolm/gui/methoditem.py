from malcolm.core import Post, Error, Return
from malcolm.gui.baseitem import BaseItem
from malcolm.gui.parameteritem import ParameterItem


class MethodItem(BaseItem):
    def get_label(self):
        if self.ref.label:
            return self.ref.label
        else:
            return super(MethodItem, self).get_label()

    def get_writeable(self):
        return self.ref.writeable

    def ref_children(self):
        """Number of child objects our ref has"""
        return len(self.ref.takes.elements)

    def create_children(self):
        for name in self.ref.takes.elements:
            meta = self.ref.takes.elements[name]
            default = self.ref.defaults.get(name, None)
            endpoint = self.endpoint + ("takes", "elements", name)
            item = ParameterItem(endpoint, meta, default)
            self.add_child(item)
            item.create_children()

    def set_value(self, value):
        args = {}
        for item in self.children:
            args[item.endpoint[-1]] = item.get_value()
            item.reset_value()
        self._state = self.RUNNING
        request = Post(path=self.endpoint, parameters=args,
                       callback=self.handle_response)
        return request

    def handle_response(self, response):
        if isinstance(response, Error):
            print("Error: %s" % response.message)
            self._state = self.ERROR
        elif isinstance(response, Return):
            print("Return: %s" % response.value)
            self._state = self.IDLE
        else:
            raise TypeError(type(response))
