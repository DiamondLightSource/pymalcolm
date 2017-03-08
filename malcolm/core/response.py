from malcolm.compat import str_
from .serializable import Serializable, deserialize_object, serialize_object


class Response(Serializable):
    """Represents a response to a Request"""

    endpoints = ["id"]

    def __init__(self, id=None):
        """Args:
            id (int): ID that the Request was sent with
        """
        self.id = self.set_id(id)

    def set_id(self, id):
        """Set the identifier for the response

        Args:
            id (int): Unique identifier for response
        """
        if id is not None:
            id = deserialize_object(id, int)
        return self.set_endpoint_data("id", id)


@Serializable.register_subclass("malcolm:core/Return:1.0")
class Return(Response):

    endpoints = ["id", "value"]

    def __init__(self, id=None, value=None):
        """
        Args:
            id (int): ID that the Request was sent with
            value: Return value of the Request
        """
        super(Return, self).__init__(id)
        self.value = self.set_value(value)

    def set_value(self, value):
        """Set the return value of the Request

        Args:
            value: Serialized value
        """
        value = serialize_object(value)
        return self.set_endpoint_data("value", value)


@Serializable.register_subclass("malcolm:core/Error:1.0")
class Error(Response):
    """Create an Error Response object with the provided parameters"""

    endpoints = ["id", "message"]

    def __init__(self, id=None, message=""):
        """
        Args:
            id (int): ID that the Request was sent with
            message(str): Error message
        """
        super(Error, self).__init__(id)
        self.message = self.set_message(message)

    def set_message(self, message):
        """Set the error message of the Response

        Args:
            message (str): Error message
        """
        message = deserialize_object(message, str_)
        return self.set_endpoint_data("message", message)


@Serializable.register_subclass("malcolm:core/Update:1.0")
class Update(Response):
    """Create an Update Response object with the provided parameters"""

    endpoints = ["id", "value"]

    def __init__(self, id=None, value=None):
        """
        Args:
            id (int): ID that the Request was sent with
            value: Serialized state of update object
        """
        super(Update, self).__init__(id)
        self.value = self.set_value(value)

    def set_value(self, value):
        """Set the return value of the Request

        Args:
            value: Serialized value
        """
        value = serialize_object(value)
        return self.set_endpoint_data("value", value)


@Serializable.register_subclass("malcolm:core/Delta:1.0")
class Delta(Response):
    """Create a Delta Response object with the provided parameters"""

    endpoints = ["id", "changes"]

    def __init__(self, id=None, changes=None):
        """
        Args:
            id (int): ID that the Request was sent with
            changes (list): list of [[path], value] pairs for changed values
        """

        super(Delta, self).__init__(id)
        self.changes = self.set_changes(changes)

    def set_changes(self, changes):
        """Set the change set for the Request

        Args:
            changes (list): list of [[path], value] pairs for changed values
        """
        # TODO: validate this
        return self.set_endpoint_data("changes", changes)
