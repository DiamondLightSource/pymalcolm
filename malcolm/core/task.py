import weakref
import time

from malcolm.core.attribute import Attribute
from malcolm.core.errors import AbortedError, ResponseError, \
    UnexpectedError, BadValueError
from malcolm.core.future import Future
from malcolm.core.loggable import Loggable
from malcolm.core.methodmeta import MethodMeta
from malcolm.core.request import Subscribe, Unsubscribe, Post, Put
from malcolm.core.response import Error, Return, Update
from malcolm.core.map import Map
from malcolm.core.spawnable import Spawnable
from malcolm.compat import queue


def match_update(value, future, required_value, bad_values=None):
    """a callback for monitoring 'when_matches' requests"""
    if bad_values is not None and value in bad_values:
        raise BadValueError(
            "Waiting for %r, got %r" % (required_value, value))

    if value == required_value:
        future.set_result(value)
        # future returned to wait_all - to be removed from wait list
        return future


class Task(Loggable, Spawnable):
    """Provides a mechanism for executing commands and setting or monitoring
        attributes on blocks. Note that queue handling is executed in the
        caller's thread (by calling wait_all). Hence this module is not
        thread safe"""

    def __init__(self, name, process):
        self.set_logger_name(name)
        self.name = name
        self.process = process
        self.q = self.process.create_queue()
        # If not None, wait for this before listening to STOPs
        self.sentinel_stop = None
        self._next_id = 1
        self._futures = {}  # dict {int id: Future}
        self._methods = {}  # dict {int id: MethodMeta}
        self._subscriptions = {}  # dict  {int id: (path, func, args)}
        # For testing, make it so start() will raise, but stop() works
        self.define_spawn_function(None)

    def _create_future(self):
        future = Future(weakref.proxy(self))
        return future

    def _get_next_id(self):
        new_id = self._next_id
        self._next_id += 1
        return new_id

    def _dispatch_request(self, request):
        future = self._create_future()
        new_id = self._get_next_id()
        self._futures[new_id] = future
        request.set_id(new_id)
        self.process.q.put(request)
        return future

    def put(self, attr, value, timeout=None):
        """"Puts a value to an attribute and returns when it completes

        Args:
            attr (Attribute): The attribute to set
            value (object): The value to set
            timeout (float): time in seconds to wait for responses, wait forever
                if None
        """
        futures = self.put_async(attr, value)
        self.wait_all(futures, timeout=timeout)

    def put_async(self, attr, value):
        """"Puts a value to an attribute and returns immediately

        Args:
            attr (Attribute): The attribute to set
            value (object): The value to set

        Returns:
             a list of one future to monitor the put completes
        """
        assert isinstance(attr, Attribute), \
            "Expected Attribute, got %r" % (attr,)

        path = attr.process_path + ["value"]
        request = Put(None, self.q, path, value)
        future = self._dispatch_request(request)
        return [future]

    def put_many(self, block, attr_values, timeout=None):
        """"Puts a number of attributes to a block at the same time, and
        returns once all values have been set

        Args:
            block (Block): The block to put attributes to
            attr_values (dict): Dictionary of {str: value} to set
            timeout (float): time in seconds to wait for responses, wait
                forever if None
        """
        futures = self.put_many_async(block, attr_values)
        self.wait_all(futures, timeout=timeout)

    def put_many_async(self, block, attr_values):
        """"Puts a number of attributes to a block at the same time, and
        returns immediately

        Args:
            block (Block): The block to put attributes to
            attr_values (dict): Dictionary of {str: value} to set

        Returns:
             a list of futures to monitor when each put completes
        """
        futures = []

        for attr_name, value in attr_values.items():
            attr = block[attr_name]
            futures += self.put_async(attr, value)

        return futures

    def when_matches(self, attr, value, bad_values=None, timeout=None):
        """ Wait for an attribute to become a given value

            Args:
                attr (Attribute): The attribute to wait for
                value (object): the value to wait for
                bad_values (list): values to raise an error on
                timeout (float): time in seconds to wait for responses, wait
                    forever if None
        """
        futures = self.when_matches_async(attr, value, bad_values)
        self.wait_all(futures, timeout)

    def when_matches_async(self, attr, value, bad_values=None):
        """ Wait for an attribute to become a given value

            Args:
                attr (Attribute): The attribute to wait for
                value (object): the value to wait for
                bad_values (list): values to raise an error on

            Returns: a list of one futures which will complete when
                all attribute values match the input
        """
        future = self._create_future()
        self.subscribe(attr, match_update, future, value, bad_values)
        return [future]

    def post(self, method, params=None, timeout=None):
        """Synchronously calls a block method

        Args:
            method (MethodMeta): the method to call
            params (dict): parameters for the call
            timeout (float): time in seconds to wait for responses, wait
                forever if None

        Returns:
            the result from 'method'
        """

        futures = self.post_async(method, params)
        self.wait_all(futures, timeout=timeout)
        return futures[0].result()

    def post_async(self, method, params=None):
        """Asynchronously calls a function on a child block

        Returns a list of one future which will proved the return value
        on completion
        """
        assert isinstance(method, MethodMeta), \
            "Expected MethodMeta, got %r" % (method,)

        path = method.process_path

        request = Post(None, self.q, path, params)
        future = self._dispatch_request(request)
        self._methods[request.id] = method
        return [future]

    def subscribe(self, attr, callback, *args):
        """Subscribe to changes in a given attribute and call
        ``callback(value, *args)`` when it changes

            Returns:
                int: an id for the subscription
        """
        assert isinstance(attr, Attribute), \
            "Expected Attribute, got %r" % (attr,)

        path = attr.process_path + ["value"]
        self.log_debug("Subscribing to %s", path)
        request = Subscribe(None, self.q, path, False)
        # If self is in args, then make weak version of it
        saved_args = []
        for arg in args:
            if arg is self:
                saved_args.append(weakref.proxy(self))
            else:
                saved_args.append(arg)
        new_id = self._get_next_id()
        self._subscriptions[new_id] = (path, callback, args)
        request.set_id(new_id)
        self.process.q.put(request)

        return new_id

    def unsubscribe(self, id_):
        """Terminates the subscription to an attribute

        Args:
            id_ (int): the identifier of the subscription to halt
        """

        self._subscriptions.pop(id_)

        request = Unsubscribe(None, self.q)
        request.set_id(id_)
        self.process.q.put(request)

    def wait_all(self, futures, timeout=None):
        """Services all futures until the list 'futures' are all done
        then returns. Calls relevant subscription callbacks as they
        come off the queue and raises an exception on abort

        Args:
            futures (Union[list, Future]): a future or list of all futures
                that the caller wants to wait for
            timeout (float): time in seconds to wait for responses, wait
                forever if None
        """
        if timeout is None:
            until = None
        else:
            until = time.time() + timeout

        if not isinstance(futures, list):
            futures = [futures]
        futures = [f for f in futures if not f.done()]

        while futures:
            self._service_futures(futures, until)

    def _service_futures(self, futures, until=None):
        if until is None:
            timeout = None
        else:
            timeout = until - time.time()
            if timeout < 0:
                timeout = 0
        response = self.q.get(True, timeout)
        if response is self.sentinel_stop:
            self.sentinel_stop = None
        elif response is Spawnable.STOP:
            if self.sentinel_stop is None:
                # This is a stop we should listen to...
                self.log_debug("wait_all received Spawnable.STOP")
                raise AbortedError()
        elif hasattr(response, "id") and response.id in self._subscriptions:
            self._invoke_callback(response, futures)
        elif hasattr(response, "id") and response.id in self._futures:
            f = self._update_future(response)
            if f in futures:
                futures.remove(f)
                if f.exception():
                    raise f.exception()
        else:
            # This might be a Return from Unsubscribe, or something else
            self.log_debug("Discarded response %s", response)

    def sleep(self, seconds):
        """Services all futures while waiting

        Args:
            seconds (float): Time to wait
        """
        until = time.time() + seconds
        try:
            while True:
                self._service_futures([], until)
        except queue.Empty:
            return

    def _update_future(self, response):
        """Called when a future is filled. Updates the future accordingly and
        removes it from the futures list
        """
        self.log_debug("future %d filled", response.id)
        f = self._futures.pop(response.id)
        method = self._methods.pop(response.id, None)
        if isinstance(response, Error):
            f.set_exception(ResponseError(response.message))
        elif isinstance(response, Return):
            result = response.value
            if method and result:
                result = Map(method.returns, result)
            f.set_result(result)
        else:
            raise UnexpectedError(
                "Future received unexpected response: %r" % response)
        return f

    def _invoke_callback(self, response, futures):
        self.log_debug("subscription %d callback", response.id)
        (path, func, args) = self._subscriptions[response.id]
        if isinstance(response, Update):
            result = func(response.value, *args)
            if func == match_update and result is not None:
                # Task's match_update callback returns a future if it has
                # filled it (other callbacks not expected to return a val)
                if result in futures:
                    futures.remove(result)
                self.unsubscribe(response.id)
        elif isinstance(response, Error):
            raise ResponseError(
                "Subscription received Error: %r" % response.message)
        else:
            raise UnexpectedError(
                "Subscription received unexpected response: %r" % response)

    def define_spawn_function(self, func, *args):
        self._initialize()
        for spawned in self._spawned:
            if not spawned.ready():
                raise UnexpectedError("Spawned %r still running" % spawned)
        self._spawn_functions = []
        self.add_spawn_function(
            func, self.make_default_stop_func(self.q), *args)

    def unsubscribe_all(self):
        ids = list(self._subscriptions)
        if ids:
            self.log_debug("Unsubscribing from ids %s", ids)
            for id_ in ids:
                self.unsubscribe(id_)

    def __del__(self):
        # Unsubscribe from anything that is still active
        self.unsubscribe_all()
