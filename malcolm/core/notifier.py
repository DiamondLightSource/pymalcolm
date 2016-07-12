from malcolm.core.loggable import Loggable
from malcolm.core.serializable import Serializable

class Notifier(Loggable, Serializable):
    def __init__(self, name):
        self.name = name
        self.set_logger_name(name)
        self.parent = None
        self.typeid = self._typeid_lookup[(type(self), args)]
        self.parent = None

    def set_parent(self, parent):
        """Sets the parent for changes to be propagated to"""
        self.set_logger_name("%s.%s" % (parent.name, self.name))
        self.parent = parent

    def on_changed(self, change, notify=True):
        """Propagate change to parent, adding self.name to paths.

        Args:
            change: [[path], value] pair for changed values
        """
        if self.parent is None:
            return
        path = change[0]
        path.insert(0, self.name)
        self.parent.on_changed(change, notify)

    def set_endpoint(self, name, value, notify=True):
        setattr(self, name, value)
        self.on_changed([[name], value], notify)
