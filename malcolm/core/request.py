from collections import OrderedDict
from malcolm.core.response import Response


class Request(object):
    """An object to interact with the attributes of a Block"""

    POST = "Post"

    def __init__(self, id_, context, response_queue, type_):
        """
        Args:
            id_(int): Unique specifier for Request
            context(): Context of request
            response_queue(Queue): Queue to return to
            type_(str): Request type e.g. get, put, post, subscribe, unsubscribe
        """

        self.id = id_
        self.context = context
        self.response_queue = response_queue
        self.type = type_
        self.fields = OrderedDict()

    def __getattr__(self, attr):
        return self.fields[attr]

    def respond_with_return(self, value=None):
        """
        Create a Response object to handle the request

        Args:
            value(): Value to set endpoint to
        """

        response = Response.Return(self.id, self.context, value=value)
        self.response_queue.put(response)

    @classmethod
    def Post(cls, id_, context, response_queue, endpoint, parameters=None):
        """
        Create a Post Request object

        Args:
            id_(int): Unique specifier for Post
            context(): Context of Post
            response_queue(Queue): Queue to return to
            endpoint(list[str]): Path to target Block substructure
            parameters(dict): List of parameters to post to an endpoint
                e.g. arguments for a Method

        Returns:
            Request object
        """

        request = Request(id_, context, response_queue, type_="Post")
        request.fields['endpoint'] = endpoint
        if parameters is not None:
            request.fields['parameters'] = parameters

        return request

    def to_dict(self):
        """Convert object attributes into a dictionary"""

        d = OrderedDict()

        d['id'] = self.id
        d['context'] = self.context.to_dict()
        d['type'] = self.type
        for field, value in self.fields.items():
            d[field] = value

        return d
