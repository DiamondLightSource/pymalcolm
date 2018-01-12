from annotypes import Anno, Any

from .serializable import Serializable, serialize_object


with Anno("ID that the Request was sent with"):
    AId = int
with Anno("Return value of the request"):
    AValue = Any
with Anno("Error message"):
    AMessage = str
with Anno("List of [[path], value] pairs for changed values"):
    AChanges = Any


class Response(Serializable):
    """Represents a response to a Request"""

    __slots__ = ["id"]

    def __init__(self, id=0):
        # type: (AId) -> None
        self.id = id


@Serializable.register_subclass("malcolm:core/Return:1.0")
class Return(Response):
    """Represents a return from a Put or Post"""

    __slots__ = ["value"]

    def __init__(self, id=0, value=None):
        # type: (AId, AValue) -> None
        super(Return, self).__init__(id)
        # Make sure it's serialized
        self.value = serialize_object(value)


@Serializable.register_subclass("malcolm:core/Error:1.0")
class Error(Response):
    """Create an Error Response object with the provided parameters"""

    __slots__ = ["message"]

    def __init__(self, id=0, message=""):
        # type: (AId, AMessage) -> None
        super(Error, self).__init__(id)
        self.message = message


@Serializable.register_subclass("malcolm:core/Update:1.0")
class Update(Response):
    """Create an Update Response object with the provided parameters"""

    __slots__ = ["value"]

    def __init__(self, id=0, value=None):
        # type: (AId, AValue) -> None
        super(Update, self).__init__(id)
        # Should already be serialized
        self.value = value


@Serializable.register_subclass("malcolm:core/Delta:1.0")
class Delta(Response):
    """Create a Delta Response object with the provided parameters"""

    __slots__ = ["changes"]

    def __init__(self, id=0, changes=None):
        # type: (AId, AChanges) -> None
        super(Delta, self).__init__(id)
        # Should already be serialized"""
        self.changes = changes

    def apply_changes_to(self, d):
        """Apply the changes to a dict like object"""
        for change in self.changes:
            path = change[0]
            if path:
                o = d
                # Update a sub-element
                for p in path[:-1]:
                    o = o.setdefault(p, {})
                if len(change) == 1:
                    # Delete
                    del o[path[-1]]
                else:
                    # Update
                    o[path[-1]] = change[1]
            else:
                # Update root
                assert len(change) == 2, "Can't delete root"
                d.clear()
                for k, v in change[1].items():
                    d[k] = v

