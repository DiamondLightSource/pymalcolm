from collections import OrderedDict


class Response(object):
    """Represents a response to a message"""

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
        """Create a Return response object with the provided parameters.

        Args:
            id (int): id from initial message
            context: context associated with id
            value: object return value (default None)
        """
        response = cls(id_, context, "Return")
        response.fields["value"] = value
        return response
