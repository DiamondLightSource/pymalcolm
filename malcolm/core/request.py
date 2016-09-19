from collections import OrderedDict

from malcolm.compat import str_
from malcolm.core.response import Return, Error, Update, Delta
from malcolm.core.serializable import Serializable, deserialize_object, \
    serialize_object


class Request(Serializable):
    """An object to interact with the attributes of a Block"""

    endpoints = ["id"]

    def __init__(self, context=None, response_queue=None):
        """
        Args:
            context(): Context of request
            response_queue(Queue): Queue to return to
        """
        self.set_id(None)
        self.context = context
        self.response_queue = response_queue

    def set_id(self, id_):
        """
        Set the identifier for the request

        Args:
            id_(int): Unique identifier for request
        """
        if id_ is not None:
            id_ = deserialize_object(id_, int)
        self.set_endpoint_data("id", id_)

    def respond_with_return(self, value=None):
        """
        Create a Return Response object to handle the request

        Args:
            value(): Value to set endpoint to
        """

        response = Return(self.id, self.context, value=value)
        self.response_queue.put(response)

    def respond_with_error(self, message):
        """
        Create an Error Response object to handle the request

        Args:
            message(str): Message explaining error
        """

        response = Error(self.id, self.context, message=message)
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
        self.set_endpoint(endpoint)

    def set_endpoint(self, endpoint):
        if endpoint is not None:
            endpoint = [deserialize_object(e, str_) for e in endpoint]
        self.set_endpoint_data("endpoint", endpoint)


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
            value(): Value to put to endpoint e.g. String, dict
        """

        super(Put, self).__init__(context, response_queue)
        self.set_endpoint(endpoint)
        self.set_value(value)

    def set_endpoint(self, endpoint):
        if endpoint is not None:
            endpoint = [deserialize_object(e, str_) for e in endpoint]
        self.set_endpoint_data("endpoint", endpoint)

    def set_value(self, value):
        self.set_endpoint_data("value", serialize_object(value))


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
                e.g. arguments for a MethodMeta
        """

        super(Post, self).__init__(context, response_queue)
        self.set_endpoint(endpoint)
        self.set_parameters(parameters)

    def set_endpoint(self, endpoint):
        if endpoint is not None:
            endpoint = [deserialize_object(e, str_) for e in endpoint]
        self.set_endpoint_data("endpoint", endpoint)

    def set_parameters(self, parameters):
        if parameters is not None:
            parameters = OrderedDict(
                (deserialize_object(k, str_), serialize_object(v))
                for k, v in parameters.items())
        self.set_endpoint_data("parameters", parameters)


@Serializable.register_subclass("malcolm:core/Subscribe:1.0")
class Subscribe(Request):
    """Create a Subscribe Request object"""

    endpoints = ["id", "endpoint", "delta"]

    def __init__(self, context=None, response_queue=None, endpoint=None,
                 delta=False):
        """
        Args:
            context: Context of Subscribe
            response_queue (Queue): Queue to return to
            endpoint (list[str]): Path to target
            delta (bool): Notify of differences only (default False)
        """

        super(Subscribe, self).__init__(context, response_queue)
        self.set_endpoint(endpoint)
        self.set_delta(delta)

    def respond_with_update(self, value):
        """
        Create an Update Response object to handle the request

        Args:
            value (dict): Dictionary describing the new structure
        """
        response = Update(self.id, self.context, value=value)
        self.response_queue.put(response)

    def respond_with_delta(self, changes):
        """
        Create a Delta Response object to handle the request

        Args:
            changes (list): list of [[path], value] pairs for changed values
        """
        response = Delta(self.id, self.context, changes=changes)
        self.response_queue.put(response)

    def set_endpoint(self, endpoint):
        if endpoint is not None:
            endpoint = [deserialize_object(e, str_) for e in endpoint]
        self.set_endpoint_data("endpoint", endpoint)

    def set_delta(self, delta):
        delta = deserialize_object(delta, bool)
        self.set_endpoint_data("delta", delta)


@Serializable.register_subclass("malcolm:core/Unsubscribe:1.0")
class Unsubscribe(Request):
    """Create an Unsubscribe Request object"""

    endpoints = ["id"]

    def __init__(self, context=None, response_queue=None):
        """
        Args:
            context: Context of the Unsubscribe
            response_queue (Queue): Queue to return to
        """
        super(Unsubscribe, self).__init__(context, response_queue)
