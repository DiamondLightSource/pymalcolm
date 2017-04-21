from contextlib import contextmanager

from .serializable import Serializable


class DummyNotifier(object):
    @property
    @contextmanager
    def changes_squashed(self):
        yield

    def add_squashed_change(self, path, data=None):
        pass


class Model(Serializable):
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

    def set_endpoint_data(self, name, value):
        with self.notifier.changes_squashed:
            # Actually set the attribute
            assert name in self.endpoints, \
                "Endpoint %r not defined for %r" % (name, self)
            setattr(self, name, value)
            # Tell the notifier what changed
            self.notifier.add_squashed_change(self.path + [name], value)
        return value


