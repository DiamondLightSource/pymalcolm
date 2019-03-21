from annotypes import Anno, Any, Serializable, FrozenOrderedDict, \
    serialize_object

with Anno("ID that the Request was sent with"):
    AId = int
with Anno("Return value of the request"):
    AValue = Any
with Anno("Error message exception"):
    AMessage = Exception
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
        self.value = value


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
        self.value = value


@Serializable.register_subclass("malcolm:core/Delta:1.0")
class Delta(Response):
    """Create a Delta Response object with the provided parameters"""

    __slots__ = ["changes"]

    def __init__(self, id=0, changes=None):
        # type: (AId, AChanges) -> None
        super(Delta, self).__init__(id)
        self.changes = changes

    def to_dict(self, dict_cls=FrozenOrderedDict):
        d = super(Delta, self).to_dict(dict_cls)
        # Serialize doesn't know to recurse here as it's not typed, so do it
        # here
        for change in d["changes"]:
            if len(change) == 2:
                change[1] = serialize_object(change[1], dict_cls)
        return d
