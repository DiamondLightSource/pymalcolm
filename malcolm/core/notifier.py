from malcolm.core.loggable import Loggable
from malcolm.core.serializable import Serializable, serialize_object

NO_VALIDATE = object()


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

    def _cast(self, value, type_):
        # Can't use metas here as we're the base class...
        if isinstance(value, dict):
            if hasattr(type_, "from_dict"):
                # turn it into the class
                value = type_.from_dict(value)
            else:
                raise ValueError("Got dict, but %s has no from_dict" % (type_,))
        assert isinstance(value, type_), \
            "Expected %s, got %s" % (type_, value)
        return value

    def set_endpoint(self, type_, name, value, notify=True):
        if isinstance(type_, list):
            assert len(type_) == 1, \
                "Can't deal with multi-type list %s" % (type_,)
            assert isinstance(value, list), \
                "Expected list, got %s" % (value,)
            value = [self._cast(v, type_[0]) for v in value]
        elif isinstance(type_, dict):
            assert len(type_) == 1, \
                "Can't deal with multi-type dict %s" % (type_,)
            ktype, vtype = list(type_.items())[0]
            assert isinstance(value, dict), \
                "Expected dict, got %s" % (value,)
            for k, v in value.items():
                assert k == self._cast(k, ktype), \
                    "Changing of key types not supported"
                value[k] = self._cast(v, vtype)
        elif type_ is not NO_VALIDATE:
            value = self._cast(value, type_)
        setattr(self, name, value)
        if hasattr(value, "set_parent"):
            value.set_parent(self, name)
        self.on_changed([[name], serialize_object(value)], notify)
