from malcolm.gui.baseitem import BaseItem


class ParameterItem(BaseItem):
    def __init__(self, endpoint, ref, default):
        super(ParameterItem, self).__init__(endpoint, ref)
        self._value = default
        self.default = default

    def get_label(self):
        if self.ref.label:
            return self.ref.label
        else:
            return super(ParameterItem, self).get_label()

    def reset_value(self):
        self._value = self.default
        self._state = self.IDLE

    def set_value(self, value):
        try:
            self._value = self.ref.validate(str(value))
        except Exception:
            self._state = self.ERROR
        else:
            self._state = self.CHANGED

    def get_value(self):
        return self._value

    def get_writeable(self):
        return getattr(self.ref, "writeable", True)
