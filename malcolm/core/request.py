import logging

from annotypes import Anno, Array, Any, TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from typing import Callable, Tuple, List

from malcolm.compat import OrderedDict, str_
from .response import Return, Error, Update, Delta, Response
from .serializable import Serializable, deserialize_object, serialize_object

# Create a module level logger
log = logging.getLogger(__name__)


with Anno("ID that should be used for any responses"):
    Id = int
with Anno("Path to target Block substructure"):
    Path = Array[str_]
with Anno("Value to put"):
    Value = Any
with Anno("Parameters to use in a method Post"):
    Parameters = Mapping[str_, Any]
with Anno("Notify of differences only"):
    Differences = bool

Callback = Callable[[Response], None]


class Request(Serializable):
    """Request object that registers a callback for when action is complete."""
    __slots__ = ["id", "callback"]

    def __init__(self, id=0):
        # type: (Id) -> None
        self.id = id

        def callback(value):
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
        message = "%s: %s" % (exception.__class__.__name__, exception)
        response = Error(id=self.id, message=message)
        log.info("Exception raised for request %s", self, exc_info=True)
        return self.callback, response

    def generate_key(self):
        """A key that will uniquely identify this request, for matching
        Subscribes up to Unsubscribes"""
        # type: () -> Tuple[Callback, int]
        key = (self.callback, self.id)
        return key


class PathRequest(Request):
    __slots__ = ["path"]

    def __init__(self, id=0, path=None):
        # type: (Id, Path) -> None
        super(PathRequest, self).__init__(id)
        self.path = path if path else []


@Serializable.register_subclass("malcolm:core/Get:1.0")
class Get(PathRequest):
    """Create a Get Request object"""
    __slots__ = []


@Serializable.register_subclass("malcolm:core/Put:1.0")
class Put(PathRequest):
    """Create a Put Request object"""
    __slots__ = ["value"]

    def __init__(self, id=0, path=None, value=None):
        # type: (Id, Path, Value) -> None
        super(Put, self).__init__(id, path)
        self.value = serialize_object(value)


@Serializable.register_subclass("malcolm:core/Post:1.0")
class Post(PathRequest):
    """Create a Post Request object"""
    __slots__ = ["parameters"]

    def __init__(self, id=0, path=None, parameters=None):
        # type: (Id, Path, Parameters) -> None
        super(Post, self).__init__(id, path)
        if parameters is not None:
            parameters = OrderedDict(
                (deserialize_object(k, str_), serialize_object(v))
                for k, v in parameters.items())
        self.parameters = parameters


@Serializable.register_subclass("malcolm:core/Subscribe:1.0")
class Subscribe(PathRequest):
    """Create a Subscribe Request object"""
    __slots__ = ["delta"]

    def __init__(self, id=0, path=None, delta=False):
        # type: (Id, Path, Differences) -> None
        super(Subscribe, self).__init__(id, path)
        self.delta = delta

    def update_response(self, value):
        # type: (Any) -> Tuple[Callback, Update]
        """Create an Update Response object to handle the request"""
        response = Update(id=self.id, value=value)
        return self.callback, response

    def delta_response(self, changes):
        # type: (List[List[List[str_], Any]]) -> Tuple[Callback, Delta]
        """"Create a Delta Response object to handle the request"""
        response = Delta(id=self.id, changes=changes)
        return self.callback, response


@Serializable.register_subclass("malcolm:core/Unsubscribe:1.0")
class Unsubscribe(Request):
    """Create an Unsubscribe Request object"""
    __slots__ = []
