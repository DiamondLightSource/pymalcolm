from contextlib import contextmanager

from annotypes import TYPE_CHECKING, Array, array_type, Any

from malcolm.compat import str_
from .serializable import Serializable
from .notifier import Notifier

if TYPE_CHECKING:
    from typing import Union, List


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
    __slots__ = []

    def set_notifier_path(self, notifier, path):
        """Sets the notifier, and the path from the path from block root

        Args:
            notifier (Notifier): The Notifier to tell when endpoint data changes
            path (list): The absolute path to get to this object
        """
        # type: (Union[Notifier, DummyNotifier], List[str]) -> None
        self.notifier = notifier
        self.path = path
        # Tell all our children too
        for name, ct in self.call_types.items():
            if ct.is_mapping:
                child = getattr(self, name)
                if isinstance(ct.typ[1], Model) and child:
                    for k, v in getattr(self, name).items():
                        v.set_notifier_path(notifier, self.path + [name, k])
            elif isinstance(ct.typ, Model):
                assert not ct.is_array, \
                    "Can't deal with Arrays of Models %s" % ct
                child = getattr(self, name)
                child.set_notifier_path(notifier, self.path + [name])

    def set_endpoint_data(self, name, value):
        # type: (str_, Any) -> Any
        try:
            ct = self.call_types[name]
        except KeyError:
            raise ValueError("Endpoint %r not defined for %r" % (name, self))
        else:
            if ct.is_array:
                # Check we have the right type
                assert isinstance(value, Array), \
                    "Expected Array, got %s" % (value,)
                expected = array_type(ct.typ)
                assert expected == value.typ, \
                    "Expected Array[%s], got %s" % (expected, value.typ)
            elif ct.is_mapping:
                # Check it is the right type
                ktype, vtype = ct.typ
                for k, v in value.items():
                    assert isinstance(k, ktype), \
                        "Expected %s, got %s" % (ktype, k)
                    assert isinstance(v, vtype), \
                        "Expected %s, got %s" % (vtype, v)
                # If we are setting structures of Models then sort notification
                if issubclass(ct.typ[1], Model):
                    # If we have old Models then stop them notifying
                    child = getattr(self, name)
                    if child:
                        for k, v in child.items():
                            v.set_notifier_path(Model.notifier, [])
                    for k, v in value.items():
                        v.set_notifier_path(self.notifier,
                                            self.path + [name, k])
            else:
                # If we are setting a Model then sort notification
                if issubclass(ct.typ, Model):
                    # If we have an old Model then stop it notifying
                    child = getattr(self, name)
                    if child:
                        child.set_notifier_path(Model.notifier, [])
                    value.set_notifier_path(self.notifier, self.path)
                # Make sure it is the right typ
                assert isinstance(value, ct.typ), \
                    "Expected %s, got %s" % (ct.typ, value)
            with self.notifier.changes_squashed:
                # Actually set the attribute
                setattr(self, name, value)
                # Tell the notifier what changed
                self.notifier.add_squashed_change(self.path + [name], value)
            return value
