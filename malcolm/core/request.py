import logging

from annotypes import Anno, Array, Any, TYPE_CHECKING, Mapping, Union, Sequence

from .response import Return, Error, Update, Delta, Response
from .serializable import Serializable, serialize_object

if TYPE_CHECKING:
    from typing import Callable, Tuple, List
    Callback = Callable[[Response], None]

# Create a module level logger
log = logging.getLogger(__name__)


with Anno("ID that should be used for any responses"):
    AId = int
with Anno("Path to target Block substructure"):
    APath = Array[str]
with Anno("Value to put"):
    AValue = Any
with Anno("Parameters to use in a method Post"):
    AParameters = Mapping[str, Any]
with Anno("Notify of differences only"):
    ADifferences = bool
UPath = Union[APath, Sequence[str], str]


class Request(Serializable):
    """Request object that registers a callback for when action is complete."""
    __slots__ = ["id", "callback"]

    # Allow id to shadow builtin id so id is a key in the serialized dict
    # noinspection PyShadowingBuiltins
    def __init__(self, id=0):
        # type: (AId) -> None
        self.id = id

        def callback(_):
            # type: (Response) -> None
            pass

        self.callback = callback

    def set_callback(self, callback):
        # type: (Callback) -> None
        """Set the callback to be called on response"""
        self.callback = callback

    def return_response(self, value=None):
        # type: (Any) -> Tuple[Callback, Return]
        """Create a Return Response object to signal a return value"""
        response = Return(id=self.id, value=value)
        return self.callback, response

    def error_response(self, exception):
        # type: (Exception) -> Tuple[Callback, Error]
        """Create an Error Response object to signal an error"""
        response = Error(id=self.id, message=exception)
        log.exception("Exception raised for request %s", self)
        return self.callback, response

    def generate_key(self):
        """A key that will uniquely identify this request, for matching
        Subscribes up to Unsubscribes"""
        # type: () -> Tuple[Callback, int]
        key = (self.callback, self.id)
        return key


class PathRequest(Request):
    __slots__ = ["path"]

    # Allow id to shadow builtin id so id is a key in the serialized dict
    # noinspection PyShadowingBuiltins
    def __init__(self, id=0, path=None):
        # type: (AId, UPath) -> None
        super(PathRequest, self).__init__(id)
        if path:
            assert isinstance(path, (list, tuple)), "Path must be given as a list or tuple"
        self.path = APath(path)



@Serializable.register_subclass("malcolm:core/Get:1.0")
class Get(PathRequest):
    """Create a Get Request object"""
    __slots__ = []


@Serializable.register_subclass("malcolm:core/Put:1.0")
class Put(PathRequest):
    """Create a Put Request object"""
    __slots__ = ["value"]

    # Allow id to shadow builtin id so id is a key in the serialized dict
    # noinspection PyShadowingBuiltins
    def __init__(self, id=0, path=None, value=None):
        # type: (AId, UPath, AValue) -> None
        super(Put, self).__init__(id, path)
        self.value = serialize_object(value)


@Serializable.register_subclass("malcolm:core/Post:1.0")
class Post(PathRequest):
    """Create a Post Request object"""
    __slots__ = ["parameters"]

    # Allow id to shadow builtin id so id is a key in the serialized dict
    # noinspection PyShadowingBuiltins
    def __init__(self, id=0, path=None, parameters=None):
        # type: (AId, UPath, AParameters) -> None
        super(Post, self).__init__(id, path)
        if parameters is not None:
            for k, v in parameters.items():
                parameters[k] = serialize_object(v)
        self.parameters = parameters


@Serializable.register_subclass("malcolm:core/Subscribe:1.0")
class Subscribe(PathRequest):
    """Create a Subscribe Request object"""
    __slots__ = ["delta"]

    # Allow id to shadow builtin id so id is a key in the serialized dict
    # noinspection PyShadowingBuiltins
    def __init__(self, id=0, path=None, delta=False):
        # type: (AId, UPath, ADifferences) -> None
        super(Subscribe, self).__init__(id, path)
        self.delta = delta

    def update_response(self, value):
        # type: (Any) -> Tuple[Callback, Update]
        """Create an Update Response object to handle the request"""
        response = Update(id=self.id, value=value)
        return self.callback, response

    def delta_response(self, changes):
        # type: (List[List[List[str], Any]]) -> Tuple[Callback, Delta]
        """"Create a Delta Response object to handle the request"""
        response = Delta(id=self.id, changes=changes)
        return self.callback, response


@Serializable.register_subclass("malcolm:core/Unsubscribe:1.0")
class Unsubscribe(Request):
    """Create an Unsubscribe Request object"""
    __slots__ = []
