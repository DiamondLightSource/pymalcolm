from malcolm.core.loggable import Loggable


class Serializable(Loggable):
    """Propagates changes to a monitoring parent"""

    def __init__(self, name):
        super(Serializable, self).__init__(logger_name=name)
        self.name = name
        self.parent = None

    def set_parent(self, parent):
        """Sets the parent for changes to be propagated to"""
        self._logger_name = "%s.%s" % (parent.name, self.name)
        self.parent = parent

    def on_changed(self, change):
        """Propagate change to parent, adding self.name to paths.

        Args:
            change: [[path], value] pair for changed values
        """
        if self.parent is None:
            return
        path = change[0]
        path.insert(0, self.name)
        self.parent.on_changed(change)
