from malcolm.core.loggable import Loggable


class Monitorable(Loggable):
    """Propagates changes to a monitoring parent"""

    def __init__(self, name):
        super(Monitorable, self).__init__(logger_name=name)
        self.name = name
        self.parent = None

    def set_parent(self, parent):
        """Sets the parent for changes to be propagated to"""
        self._logger_name = "%s.%s" % (parent.name, self.name)
        self.parent = parent

    def on_changed(self, changes):
        """Propagate changes to parent, adding self.name to paths.

        Args:
            changes: list of [[path], value] pairs for changed values
        """
        if self.parent is None:
            return
        for (path, change) in changes:
            path.insert(0, self.name)
        self.parent.on_changed(changes)
