from collections import OrderedDict


class Response(object):
    """Represents a response to a message"""
    RETURN = "Return"

    def __init__(self, id_, context, type_):
        self.id_ = id_
        self.type_ = type_
        self.context = context
        self.fields = OrderedDict()

    def to_dict(self):
        serialized = OrderedDict()
        serialized["id"] = self.id_
        serialized["type"] = self.type_
        for (field, value) in self.fields.items():
            serialized[field] = value
        return serialized

    def __getattr__(self, attr):
        return self.fields[attr]

    @classmethod
    def Return(cls, id_, context, value=None):
        """Create a Return Response object with the provided parameters.

        Args:
            id_ (int): id from initial message
            context: context associated with id
            value: object return value (default None)
        """
        response = cls(id_, context, "Return")
        response.fields["value"] = value
        return response

    @classmethod
    def Error(cls, id_, context, message):
        """
        Create an Error Response object with the provided parameters.

        Args:
            id_(int): ID from initial message
            context(): Context associated with ID
            message(str): Error message
        """

        response = cls(id_, context, "Error")
        response.fields["message"] = message
        return response

    @classmethod
    def Update(cls, id_, context, value):
        """
        Create an Update Response object with the provided parameters.

        Args:
            id_ (int): id from intial message
            context: Context associated with id
            value (dict): Serialized state of update object
        """
        response = cls(id_, context, "Update")
        response.fields["value"] = value
        return response

    @classmethod
    def Delta(cls, id_, context, changes):
        """
        Create a Delta Response object with the provided parameters.

        Args:
            id_ (int): id from initial message
            context: Context associated with id
            changes (list): list of [[path], value] pairs for changed values
        """
        response = cls(id_, context, "Delta")
        response.fields["changes"] = changes
        return response

    @classmethod
    def from_dict(cls, d):
        """Create a Response instance from a serialized version

        Args:
            d (dict): output of self.to_dict()
        """
        response = cls(id_=d["id"], context=None, type_=d["type"])
        for field in [f for f in d.keys() if f not in ["id", "type"]]:
            response.fields[field] = d[field]
        return response
