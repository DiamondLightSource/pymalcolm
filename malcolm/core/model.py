from contextlib import contextmanager

from .loggable import Loggable
from .serializable import Serializable


def set_notifier_path(o, notifier, notifier_path):
    """Set notifier path recursively on object

    Args:
        o (Model): The object to start with
        notifier (Notifier): The notifier to set
        notifier_path (list): The path to get to this object from block
    """
    if isinstance(o, dict):
        # Need to recurse down
        for k, v in o.items():
            set_notifier_path(v, notifier, notifier_path + [k])
    elif isinstance(o, list):
        # Need to recurse down
        for i, v in enumerate(o):
            set_notifier_path(v, notifier, notifier_path + [i])
    elif hasattr(o, "set_notifier_path"):
        # This will do all the sub layers for us
        o.set_notifier_path(notifier, notifier_path)


class DummyNotifier(object):
    @property
    @contextmanager
    def changes_squashed(self):
        yield

    def add_squashed_change(self, path, data=None):
        pass


class Model(Loggable, Serializable):
    notifier = DummyNotifier()
    path = []

    def set_notifier_path(self, notifier, path):
        """Sets the notifier, and the path from the path from block root

        Args:
            notifier (Notifier): The Notifier to tell when endpoint data changes
            path (list): The absolute path to get to this object
        """
        self.notifier = notifier
        self.path = list(path)
        self.set_logger_name(".".join(self.path))
        for endpoint in self.endpoints:
            set_notifier_path(self[endpoint], notifier, self.path + [endpoint])

    def set_endpoint_data(self, name, value):
        with self.notifier.changes_squashed:
            # Set the notifier for the child
            if self.path:
                path = self.path + [name]
                set_notifier_path(value, self.notifier, path)
                # Tell the notifier what changed
                self.notifier.add_squashed_change(path, value)
            # Actually set the attribute
            super(Model, self).set_endpoint_data(name, value)
        return value


