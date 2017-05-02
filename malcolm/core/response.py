from malcolm.compat import str_
from .serializable import Serializable, deserialize_object, serialize_object


class Response(Serializable):
    """Represents a response to a Request"""

    endpoints = ["id"]
    __slots__ = endpoints

    id = None

    def __init__(self, id=None):
        """Args:
            id (int): ID that the Request was sent with
        """
        self.set_id(id)

    def set_id(self, id):
        """Set the identifier for the response

        Args:
            id (int): Unique identifier for response
        """
        if id is not None:
            id = deserialize_object(id, int)
        self.id = id


@Serializable.register_subclass("malcolm:core/Return:1.0")
class Return(Response):

    endpoints = ["id", "value"]
    __slots__ = endpoints

    value = None

    def __init__(self, id=None, value=None):
        """
        Args:
            id (int): ID that the Request was sent with
            value: Return value of the Request
        """
        super(Return, self).__init__(id)
        self.set_value(value)

    def set_value(self, value):
        """Set the return value of the Request

        Args:
            value: Serialized value
        """
        self.value = serialize_object(value)


@Serializable.register_subclass("malcolm:core/Error:1.0")
class Error(Response):
    """Create an Error Response object with the provided parameters"""

    endpoints = ["id", "message"]
    __slots__ = endpoints

    message = None

    def __init__(self, id=None, message=""):
        """
        Args:
            id (int): ID that the Request was sent with
            message(str): Error message
        """
        super(Error, self).__init__(id)
        self.set_message(message)

    def set_message(self, message):
        """Set the error message of the Response

        Args:
            message (str): Error message
        """
        self.message = deserialize_object(message, str_)


@Serializable.register_subclass("malcolm:core/Update:1.0")
class Update(Response):
    """Create an Update Response object with the provided parameters"""

    endpoints = ["id", "value"]
    __slots__ = endpoints

    value = None

    def __init__(self, id=None, value=None):
        """
        Args:
            id (int): ID that the Request was sent with
            value: Serialized state of update object
        """
        super(Update, self).__init__(id)
        self.set_value(value)

    def set_value(self, value):
        """Set the return value of the Request. Should already be serialized

        Args:
            value: Serialized value
        """
        self.value = value


@Serializable.register_subclass("malcolm:core/Delta:1.0")
class Delta(Response):
    """Create a Delta Response object with the provided parameters"""

    endpoints = ["id", "changes"]
    __slots__ = endpoints

    changes = None

    def __init__(self, id=None, changes=None):
        """
        Args:
            id (int): ID that the Request was sent with
            changes (list): list of [[path], value] pairs for changed values
        """

        super(Delta, self).__init__(id)
        self.set_changes(changes)

    def set_changes(self, changes):
        """Set the change set for the Request, should already be serialized

        Args:
            changes (list): list of [[path], value] pairs for changed values
        """
        self.changes = changes
