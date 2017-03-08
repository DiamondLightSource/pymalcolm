from .loggable import Loggable
from .serializable import Serializable


def set_notifier_path(o, notifier, notifier_path):
    """Set notifier path recursively on object

    Args:
        o (Model): The object to start with
        notifier (Notifier): The notifier to set
        notifier_path (list): The path to get to this object from block
    """
    if hasattr(o, "set_notifier_path"):
        # This will do all the sub layers for us
        o.set_notifier_path(notifier, notifier_path)
    elif isinstance(o, dict):
        # Need to recurse down
        for k, v in o.items():
            set_notifier_path(v, notifier, notifier_path + [k])
    elif isinstance(o, list):
        # Need to recurse down
        for i, v in enumerate(o):
            set_notifier_path(v, notifier, notifier_path + [i])


class Model(Loggable, Serializable):
    notifier = None
    path = None

    def set_notifier_path(self, notifier, path):
        """Sets the notifier, and the path from the path from block root

        Args:
            notifier (Notifier): The Notifier to tell when endpoint data changes
            path (list): The path to get to this object from block
        """
        self.notifier = notifier
        self.path = list(path)
        self.set_logger_name(".".join(self.path))
        for name in self:
            set_notifier_path(self[name], notifier, self.path + [name])

    def set_endpoint_data(self, name, value):
        if self.notifier:
            # Set the notifier for the child
            path = self.path + [name]
            set_notifier_path(value, self.notifier, path)
            # Get notifier to run this with its lock taken
            return self.notifier.make_endpoint_change(
                self.set_endpoint_data_locked, path, value)
        else:
            # Just run the function ourself
            return self.set_endpoint_data_locked(name, value)

    def set_endpoint_data_locked(self, name, value):
        return super(Model, self).set_endpoint_data(name, value)
