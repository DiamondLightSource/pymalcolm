from malcolm.core.loggable import Loggable
from malcolm.core.serializable import Serializable, serialize_object


class Notifier(Loggable, Serializable):

    endpoints = []

    def set_parent(self, parent, name):
        """Sets the parent for changes to be propagated to"""
        self.parent = parent
        self.name = name
        self.set_logger_name(name)

    def set_logger_name(self, name):
        super(Notifier, self).set_logger_name(name)
        for endpoint in self.endpoints:
            attr = getattr(self, endpoint)
            if hasattr(attr, "set_logger_name"):
                attr.set_logger_name("%s.%s" % (name, endpoint))

    def on_changed(self, change, notify=True):
        """Propagate change to parent, adding self.name to paths.

        Args:
            change: [[path], value] pair for changed values
        """
        if not hasattr(self, "parent"):
            return
        path = change[0]
        path.insert(0, self.name)
        self.parent.on_changed(change, notify)

    def set_endpoint(self, name, value, notify=True):
        setattr(self, name, value)
        self.on_changed([[name], serialize_object(value)], notify)
