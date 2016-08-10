from malcolm.core.loggable import Loggable
from malcolm.core.serializable import Serializable, serialize_object


class Monitorable(Loggable, Serializable):
    _parent = None
    _name = None

    def set_parent(self, parent, name):
        """Sets the parent for changes to be propagated to"""
        self.set_logger_name(name)
        self._parent = parent
        self._name = name

    def path_relative_to(self, elder):
        """Find the path of this item relative to some elder parent."""
        path = [self._name]
        if self._parent is not elder:
            # Go up the tree if we can
            if hasattr(self._parent, "path_relative_to"):
                path = self._parent.path_relative_to(elder) + path
            else:
                raise ValueError(
                    "Reached the top of the tree %s, and it isn't equal to %s" %
                    (self, elder))
        return path

    def set_logger_name(self, name):
        super(Monitorable, self).set_logger_name(name)
        for endpoint in self:
            attr = self[endpoint]
            if hasattr(attr, "set_logger_name"):
                attr.set_logger_name("%s.%s" % (name, endpoint))

    def report_changes(self, *changes):
        """Propagate change to parent, adding self.name to paths.

        Args:
            changes: [[[path], value]] pairs for changed values
        """
        if self._parent is None:
            return
        for change in changes:
            path = change[0]
            path.insert(0, self._name)
        self._parent.report_changes(*changes)

    def set_endpoint_data(self, name, value, notify=True):
        # set parent first so that we don't put something in the tree that
        # doesn't know how to get the path to the top of the tree
        if hasattr(value, "set_parent"):
            value.set_parent(self, name)
        super(Monitorable, self).set_endpoint_data(name, value)
        if notify:
            self.report_changes([[name], serialize_object(value)])

    def apply_changes(self, *changes):
        serialized_changes = []
        for path, value in changes:
            ob = self
            for node in path[:-1]:
                ob = ob[node]
            attr = path[-1]
            setter = getattr(ob, "set_%s" % attr)
            setter(value, notify=False)
            serialized = serialize_object(ob[attr])
            serialized_changes.append([path, serialized])
        self.report_changes(*serialized_changes)

