from malcolm.core.serializable import Serializable


class Response(Serializable):
    """Represents a response to a message"""

    endpoints = ["id"]

    def __init__(self, id_=None, context=None):
        self.id_ = id_
        self.context = context

    def __repr__(self):
        return self.to_dict().__repr__()

    def get_endpoint(self, endpoint):
        if endpoint == "id":
            return self.id_
        return getattr(self, endpoint)

    def set_id(self, id_):
        self.id_ = id_


@Serializable.register_subclass("malcolm:core/Return:1.0")
class Return(Response):

    endpoints = ["id", "value"]

    def __init__(self, id_=None, context=None, value=None):
        super(Return, self).__init__(id_, context)
        self.value = value

    def set_value(self, value):
        self.value = value


@Serializable.register_subclass("malcolm:core/Error:1.0")
class Error(Response):
    """Create an Error Response object with the provided parameters"""

    endpoints = ["id", "message"]

    def __init__(self, id_=None, context=None, message=None):
        """
        Args:
            id_(int): ID from initial message
            context(): Context associated with ID
            message(str): Error message
        """
        super(Error, self).__init__(id_, context)
        self.message = message

    def set_message(self, message):
        self.message = message


@Serializable.register_subclass("malcolm:core/Update:1.0")
class Update(Response):
    """Create an Update Response object with the provided parameters"""

    endpoints = ["id", "value"]

    def __init__(self, id_=None, context=None, value=None):
        """
        Args:
            id_ (int): id from initial message
            context: Context associated with id
            value (dict): Serialized state of update object
        """

        super(Update, self).__init__(id_, context)
        self.value = value

    def set_value(self, value):
        self.value = value


@Serializable.register_subclass("malcolm:core/Delta:1.0")
class Delta(Response):
    """Create a Delta Response object with the provided parameters"""

    endpoints = ["id", "changes"]

    def __init__(self, id_=None, context=None, changes=None):
        """
        Args:
            id_ (int): id from initial message
            context: Context associated with id
            changes (list): list of [[path], value] pairs for changed values
        """

        super(Delta, self).__init__(id_, context)
        self.changes = changes

    def set_changes(self, changes):
        self.changes = changes
