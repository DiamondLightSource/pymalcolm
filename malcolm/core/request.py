import logging

from malcolm.compat import OrderedDict, str_
from .response import Return, Error, Update, Delta
from .serializable import Serializable, deserialize_object, serialize_object

# Create a module level logger
log = logging.getLogger(__name__)


class Request(Serializable):
    """Request object that registers a callback for when action is complete."""

    endpoints = ["id"]
    __slots__ = endpoints

    id = None
    callback = None

    def __init__(self, id=None, callback=None):
        """
        Args:
            id (int): ID that context(): Context of request
            callback (function): Callback for when the response is available

        callback(response) will be called when the request is completed
        """
        self.set_id(id)
        self.set_callback(callback)

    def set_id(self, id):
        """Set the identifier for the request

        Args:
            id (int): Unique identifier for request
        """
        if id is not None:
            id = deserialize_object(id, int)
        self.id = id

    def set_callback(self, callback):
        """Set the callback to be called on response"""
        if callback is None:
            def callback(value):
                pass
        self.callback = callback

    def return_response(self, value=None):
        """Create a Return Response object to signal a return value

        Args:
            value (object): Return value
        """
        response = Return(id=self.id, value=value)
        return self.callback, response

    def error_response(self, exception):
        """Create an Error Response object to signal an error

        Args:
            exception (Exception): Message explaining error
        """

        response = Error(id=self.id, message=str(exception))
        log.exception("Exception raised for request %s", self)
        return self.callback, response

    def generate_key(self):
        """A key that will uniquely identify this request, for matching
        Subscribes up to Unsubscribes"""
        key = (self.callback, self.id)
        return key


class PathRequest(Request):
    """Create a Get Request object"""

    endpoints = ["id", "path"]
    __slots__ = endpoints

    path = None

    def __init__(self, id=None, path=None, callback=None):
        """
        Args:
            id (int): Unique identifier for request
            path (list): [`str`] Path to target Block substructure
            callback (function): Callback for when the response is available
        """
        super(PathRequest, self).__init__(id, callback)
        self.set_path(path)

    def set_path(self, path):
        """Set the path to the endpoint to operate on

        Args:
            path (list): [`str`] Path to target Block substructure
        """
        self.path = [deserialize_object(e, str_) for e in path]


@Serializable.register_subclass("malcolm:core/Get:1.0")
class Get(PathRequest):
    """Create a Get Request object"""


@Serializable.register_subclass("malcolm:core/Put:1.0")
class Put(PathRequest):
    """Create a Put Request object"""

    endpoints = ["id", "path", "value"]
    __slots__ = endpoints

    value = None

    def __init__(self, id=None, path=(), value=None, callback=None):
        """
        Args:
            id (int): Unique identifier for request
            path (list): [`str`] Path to target Block substructure
            value: Value to put to path
            callback (function): Callback for when the response is available
        """
        super(Put, self).__init__(id, path, callback)
        self.set_value(value)

    def set_value(self, value):
        """Value to Put to endpoint

        Args:
            value: Value to put to path
        """
        self.value = serialize_object(value)


@Serializable.register_subclass("malcolm:core/Post:1.0")
class Post(PathRequest):
    """Create a Post Request object"""

    endpoints = ["id", "path", "parameters"]
    __slots__ = endpoints

    parameters = None

    def __init__(self, id=None, path=(), parameters=None, callback=None):
        """
        Args:
            id (int): Unique identifier for request
            path (list): [`str`] Path to target Block substructure
            parameters: Parameters to Post
            callback (function): Callback for when the response is available
        """
        super(Post, self).__init__(id, path, callback)
        self.set_parameters(parameters)

    def set_parameters(self, parameters):
        """Parameters to Post to endpoint

        Args:
            parameters: Value to post to path
        """
        if parameters is not None:
            parameters = OrderedDict(
                (deserialize_object(k, str_), serialize_object(v))
                for k, v in parameters.items())
        self.parameters = parameters


@Serializable.register_subclass("malcolm:core/Subscribe:1.0")
class Subscribe(PathRequest):
    """Create a Subscribe Request object"""

    endpoints = ["id", "path", "delta"]
    __slots__ = endpoints

    delta = None

    def __init__(self, id=None, path=(), delta=False, callback=None):
        """Args:
            id (int): Unique identifier for request
            path (list): [`str`] Path to target Block substructure
            delta (bool): Notify of differences only (default False)
            callback (function): Callback for when the response is available
        """

        super(Subscribe, self).__init__(id, path, callback)
        self.set_delta(delta)

    def set_delta(self, delta):
        """Whether to ask for delta responses or not

        Args:
            delta: If true then request Delta responses, otherwise Update
        """
        self.delta = deserialize_object(delta, bool)

    def update_response(self, value):
        """Create an Update Response object to handle the request

        Args:
            value: Serialized new value
        """
        response = Update(id=self.id, value=value)
        return self.callback, response

    def delta_response(self, changes):
        """Create a Delta Response object to handle the request

        Args:
            changes (list): list of [[path], value] pairs for changed values
        """
        response = Delta(id=self.id, changes=changes)
        return self.callback, response


@Serializable.register_subclass("malcolm:core/Unsubscribe:1.0")
class Unsubscribe(Request):
    """Create an Unsubscribe Request object"""
