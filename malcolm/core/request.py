from malcolm.core.serializable import Serializable
from malcolm.core.response import Return, Error, Update, Delta


class Request(Serializable):
    """An object to interact with the attributes of a Block"""

    endpoints = ["id"]

    def __init__(self, context=None, response_queue=None):
        """
        Args:
            context(): Context of request
            response_queue(Queue): Queue to return to
        """

        self.id_ = None
        self.context = context
        self.response_queue = response_queue

    def set_id(self, id_):
        """
        Set the identifier for the request

        Args:
            id_(int): Unique identifier for request
        """

        self.id_ = id_

    def to_dict(self, **overrides):
        return super(Request, self).to_dict(id=self.id_)

    def respond_with_return(self, value=None):
        """
        Create a Return Response object to handle the request

        Args:
            value(): Value to set endpoint to
        """

        response = Return(self.id_, self.context, value=value)
        self.response_queue.put(response)

    def respond_with_error(self, message):
        """
        Create an Error Response object to handle the request

        Args:
            message(str): Message explaining error
        """

        response = Error(self.id_, self.context, message=message)
        self.response_queue.put(response)

    def respond_with_update(self, value):
        """
        Create an Update Response object to handle the request

        Args:
            value (dict): Dictionary describing the new structure
        """
        response = Update(self.id_, self.context, value=value)
        self.response_queue.put(response)

    def respond_with_delta(self, changes):
        """
        Create a Delta Response object to handle the request

        Args:
            changes (list): list of [[path], value] pairs for changed values
        """
        response = Delta(self.id_, self.context, changes=changes)
        self.response_queue.put(response)

    def __repr__(self):
        return self.to_dict().__repr__()


@Serializable.register_subclass("malcolm:core/Get:1.0")
class Get(Request):
    """Create a Get Request object"""

    endpoints = ["id", "endpoint"]

    def __init__(self, context=None, response_queue=None, endpoint=None):
        """
        Args:
            context(): Context of Get
            response_queue(Queue): Queue to return to
            endpoint(list[str]): Path to target Block substructure
        """

        super(Get, self).__init__(context, response_queue)
        self.endpoint = endpoint

    def set_endpoint(self, endpoint):
        self.endpoint = endpoint


@Serializable.register_subclass("malcolm:core/Put:1.0")
class Put(Request):
    """Create a Put Request object"""

    endpoints = ["id", "endpoint", "value"]

    def __init__(self, context=None, response_queue=None,
                 endpoint=None, value=None):
        """
        Args:
            context(): Context of Put
            response_queue(Queue): Queue to return to
            endpoint(list[str]): Path to target Block substructure
            value(str): Value to put to endpoint
        """

        super(Put, self).__init__(context, response_queue)
        self.endpoint = endpoint
        self.value = value

    def set_endpoint(self, endpoint):
        self.endpoint = endpoint

    def set_value(self, value):
        self.value = value


@Serializable.register_subclass("malcolm:core/Post:1.0")
class Post(Request):
    """Create a Post Request object"""

    endpoints = ["id", "endpoint", "parameters"]

    def __init__(self, context=None, response_queue=None,
                 endpoint=None, parameters=None):
        """
        Args:
            context(): Context of Post
            response_queue(Queue): Queue to return to
            endpoint(list[str]): Path to target Block substructure
            parameters(dict): List of parameters to post to an endpoint
                e.g. arguments for a Method
        """

        super(Post, self).__init__(context, response_queue)
        self.endpoint = endpoint
        self.parameters = parameters

    def set_endpoint(self, endpoint):
        self.endpoint = endpoint

    def set_parameters(self, parameters):
        self.parameters = parameters


@Serializable.register_subclass("malcolm:core/Subscribe:1.0")
class Subscribe(Request):
    """Create a Subscribe Request object"""

    endpoints = ["id", "endpoint", "delta"]

    def __init__(self, context=None, response_queue=None, endpoint=None, delta=False):
        """
        Args:
            context: Context of Subscribe
            response_queue (Queue): Queue to return to
            endpoint (list[str]): Path to target
            delta (bool): Notify of differences only (default False)
        """

        super(Subscribe, self).__init__(context, response_queue)
        self.endpoint = endpoint
        self.delta = delta

    def set_endpoint(self, endpoint):
        self.endpoint = endpoint

    def set_delta(self, delta):
        self.delta = delta
