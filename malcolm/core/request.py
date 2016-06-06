from collections import OrderedDict
from malcolm.core.response import Response


class Request(object):
    """An object to interact with the attributes of a Block"""

    POST = "Post"

    def __init__(self, context, response_queue, type_):
        """
        Args:
            context(): Context of request
            response_queue(Queue): Queue to return to
            type_(str): Request type e.g. get, put, post, subscribe, unsubscribe
        """

        self.id_ = None
        self.context = context
        self.response_queue = response_queue
        self.type_ = type_
        self.fields = OrderedDict()

    def __getattr__(self, attr):
        return self.fields[attr]

    def set_id(self, id_):
        """
        Set the identifier for the request

        Args:
            id_(int): Unique identifier for request
        """

        self.id_ = id_

    def respond_with_return(self, value=None):
        """
        Create a Return Response object to handle the request

        Args:
            value(): Value to set endpoint to
        """

        response = Response.Return(self.id_, self.context, value=value)
        self.response_queue.put(response)

    def respond_with_error(self, error_message=None):
        """
        Create an Error Response object to handle the request

        Args:
            error_message(str): Message explaining error
        """

        response = Response.Error(self.id_, self.context, error_message=error_message)
        self.response_queue.put(response)

    @classmethod
    def Get(cls, context, response_queue, endpoint):
        """
        Create a Get Request object

        Args:
            context(): Context of Get
            response_queue(Queue): Queue to return to
            endpoint(list[str]): Path to target Block substructure

        Returns:
            Request object
        """

        request = Request(context, response_queue, type_="Get")
        request.fields['endpoint'] = endpoint

        return request

    @classmethod
    def Post(cls, context, response_queue, endpoint, parameters=None):
        """
        Create a Post Request object

        Args:
            context(): Context of Post
            response_queue(Queue): Queue to return to
            endpoint(list[str]): Path to target Block substructure
            parameters(dict): List of parameters to post to an endpoint
                e.g. arguments for a Method

        Returns:
            Request object
        """

        request = Request(context, response_queue, type_="Post")
        request.fields['endpoint'] = endpoint
        if parameters is not None:
            request.fields['parameters'] = parameters

        return request

    def to_dict(self):
        """Convert object attributes into a dictionary"""

        d = OrderedDict()

        d['id'] = self.id_
        d['type'] = self.type_
        for field, value in self.fields.items():
            d[field] = value

        return d

    @classmethod
    def from_dict(cls, d):
        """Create a Request instance from a serialized version

        Args:
            d (dict): output of self.to_dict()
        """
        request = cls(context=None, response_queue=None, type_=d["type"])
        request.set_id(d['id'])
        for field in [f for f in d.keys() if f not in ["id", "type"]]:
            request.fields[field] = d[field]
        return request
