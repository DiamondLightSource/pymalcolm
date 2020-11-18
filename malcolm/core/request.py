import logging
from typing import Any, Callable, List, Mapping, Sequence, Tuple, Union

from annotypes import Anno, Array, Serializable

from .response import Delta, Error, Response, Return, Update

Callback = Callable[[Response], None]

# Create a module level logger
log = logging.getLogger(__name__)


with Anno("ID that should be used for any responses"):
    AId = int
with Anno("Path to target Block substructure"):
    APath = Union[Array[str]]
with Anno("Value to put"):
    AValue = Any
with Anno("If set then return the current value in Return when Put completes"):
    AGet = bool
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
    def __init__(self, id: AId = 0) -> None:
        self.id = id

        def callback(response: Response) -> None:
            pass

        self.callback: Callback = callback

    def set_callback(self, callback: Callback) -> None:
        """Set the callback to be called on response"""
        self.callback = callback

    def return_response(self, value: Any = None) -> Tuple[Callback, Return]:
        """Create a Return Response object to signal a return value"""
        response = Return(id=self.id, value=value)
        return self.callback, response

    def error_response(self, exception: Exception) -> Tuple[Callback, Error]:
        """Create an Error Response object to signal an error"""
        response = Error(id=self.id, message=exception)
        log.exception("Exception raised for request %s", self)
        return self.callback, response

    def generate_key(self) -> Tuple[Callback, int]:
        """A key that will uniquely identify this request, for matching
        Subscribes up to Unsubscribes"""
        key = (self.callback, self.id)
        return key


class PathRequest(Request):
    __slots__ = ["path"]

    # Allow id to shadow builtin id so id is a key in the serialized dict
    # noinspection PyShadowingBuiltins
    def __init__(self, id: AId = 0, path: UPath = None) -> None:
        super().__init__(id)
        self.path = APath(path)
        if not self.path:
            raise ValueError(
                "Expected a path with at least 1 element, got %s" % list(self.path)
            )


@Serializable.register_subclass("malcolm:core/Get:1.0")
class Get(PathRequest):
    """Create a Get Request object"""

    __slots__: List[str] = []


@Serializable.register_subclass("malcolm:core/Put:1.0")
class Put(PathRequest):
    """Create a Put Request object"""

    __slots__ = ["value", "get"]

    # Allow id to shadow builtin id so id is a key in the serialized dict
    # noinspection PyShadowingBuiltins
    def __init__(
        self, id: AId = 0, path: UPath = None, value: AValue = None, get: AGet = False
    ) -> None:
        super().__init__(id, path)
        self.value = value
        self.get = get


@Serializable.register_subclass("malcolm:core/Post:1.0")
class Post(PathRequest):
    """Create a Post Request object"""

    __slots__ = ["parameters"]

    # Allow id to shadow builtin id so id is a key in the serialized dict
    # noinspection PyShadowingBuiltins
    def __init__(
        self, id: AId = 0, path: UPath = None, parameters: AParameters = None
    ) -> None:
        super().__init__(id, path)
        self.parameters = parameters


@Serializable.register_subclass("malcolm:core/Subscribe:1.0")
class Subscribe(PathRequest):
    """Create a Subscribe Request object"""

    __slots__ = ["delta"]

    # Allow id to shadow builtin id so id is a key in the serialized dict
    # noinspection PyShadowingBuiltins
    def __init__(
        self, id: AId = 0, path: UPath = None, delta: ADifferences = False
    ) -> None:
        super().__init__(id, path)
        self.delta = delta

    def update_response(self, value: Any) -> Tuple[Callback, Update]:
        """Create an Update Response object to handle the request"""
        response = Update(id=self.id, value=value)
        return self.callback, response

    def delta_response(
        self, changes: List[List[Union[List[str], Any]]]
    ) -> Tuple[Callback, Delta]:
        """"Create a Delta Response object to handle the request"""
        response = Delta(id=self.id, changes=changes)
        return self.callback, response


@Serializable.register_subclass("malcolm:core/Unsubscribe:1.0")
class Unsubscribe(Request):
    """Create an Unsubscribe Request object"""

    __slots__: List[str] = []
