import weakref
import time

from malcolm.core.attribute import Attribute
from malcolm.core.future import Future
from malcolm.core.loggable import Loggable
from malcolm.core.methodmeta import MethodMeta
from malcolm.core.request import Subscribe, Unsubscribe, Post, Put
from malcolm.core.response import Error, Return, Update
from malcolm.core.spawnable import Spawnable
from malcolm.compat import queue


def match_update(value, task, future, required_value, subscription_ids,
                 bad_values=None):
    """a callback for monitoring 'when_matches' requests"""
    if bad_values is not None:
        assert value not in bad_values, \
            "Waiting for %r, got %r" % (required_value, value)

    ret_val = None
    if value == required_value:
        future.set_result(value)
        task.unsubscribe(subscription_ids[0])
        # future returned to wait_all - to be removed from wait list
        ret_val = future
    return ret_val


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
        self._next_id = 0
        self._futures = {}  # dict {int id: Future}
        self._subscriptions = {}  # dict  {int id: (endpoint, func, args)}
        # For testing, make it so start() will raise, but stop() works
        self.define_spawn_function(None)

    def _save_future(self):
        """ stores the future with unique id"""
        future = Future(None)
        new_id = self._next_id
        self._next_id += 1
        self._futures[new_id] = future
        return new_id, future

    def _save_subscription(self, endpoint, function, *args):
        """ stores a subscription with unique id"""
        new_id = self._next_id
        self._next_id += 1
        self._subscriptions[new_id] = (endpoint, function, args)
        return new_id

    def put(self, attr, value, timeout=None):
        """"Puts a value to an attribute and returns when it completes

        Args:
            attr (Attribute): The attribute to set
            value (object): The value to set
            timeout (Float) time in seconds to wait for responses, wait forever
                if None
        """
        f = self.put_async(attr, value)
        self.wait_all(f, timeout=timeout)

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

        endpoint = attr.path_relative_to(self.process) + ["value"]
        request = Put(None, self.q, endpoint, value)
        new_id, f = self._save_future()
        request.set_id(new_id)
        self.process.q.put(request)

        return [f]

    def put_many(self, block, attr_values, timeout=None):
        """"Puts a number of attributes to a block at the same time, and
        returns once all values have been set

        Args:
            block (Block): The block to put attributes to
            attr_values (dict): Dictionary of {str: value} to set
            timeout (float) time in seconds to wait for responses, wait
                forever if None
        """
        f = self.put_many_async(block, attr_values)
        self.wait_all(f, timeout=timeout)

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
                timeout (Float) time in seconds to wait for responses, wait
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
        _, f = self._save_future()
        subscription_ids = []
        subscription_id = self.subscribe(
            attr, match_update, self, f, value, subscription_ids, bad_values)
        subscription_ids.append(subscription_id)

        return [f]

    def post(self, method, params=None, timeout=None):
        """Synchronously calls a block method

            Args:
                method (MethodMeta): the method to call
                params (dict): parameters for the call
                timeout (Float) time in seconds to wait for responses, wait
                    forever if None

            Returns:
                the result from 'method'"""

        f = self.post_async(method, params)
        self.wait_all(f, timeout=timeout)
        # TODO: should this be f.get?
        return f

    def post_async(self, method, params=None):
        """Asynchronously calls a function on a child block

            Returns a list of one future which will proved the return value
            on completion"""
        assert isinstance(method, MethodMeta), \
            "Expected MethodMeta, got %r" % (method,)

        endpoint = method.path_relative_to(self.process)

        request = Post(None, self.q, endpoint, params)
        new_id, f = self._save_future()
        request.set_id(new_id)
        self.process.q.put(request)

        return [f]

    def subscribe(self, attr, callback, *args):
        """Subscribe to changes in a given attribute and call
        ``callback(value, *args)`` when it changes

            Returns:
                int: an id for the subscription
        """
        assert isinstance(attr, Attribute), \
            "Expected Attribute, got %r" % (attr,)

        endpoint = attr.path_relative_to(self.process) + ["value"]
        self.log_debug("Subscribing to %s", endpoint)
        request = Subscribe(None, self.q, endpoint, False)
        # If self is in args, then make weak version of it
        saved_args = []
        for arg in args:
            if arg is self:
                saved_args.append(weakref.proxy(self))
            else:
                saved_args.append(arg)
        new_id = self._save_subscription(endpoint, callback, *saved_args)
        request.set_id(new_id)
        self.process.q.put(request)

        return new_id

    def unsubscribe(self, id_):
        """Terminates the subscription to an attribute

            Args:
                id_ (Int): the identifier of the subscription to halt"""

        self._subscriptions.pop(id_)

        request = Unsubscribe(None, self.q)
        request.set_id(id_)
        self.process.q.put(request)

    def wait_all(self, futures, timeout=None):
        """services all futures until the list 'futures' are all done
            then returns. Calls relevant subscription callbacks as they
            come off the queue and raises an exception on abort

            Args:
                futures ([Future] or Future): a future or list of all futures
                    that the caller wants to wait for
                timeout (Float) time in seconds to wait for responses, wait
                    forever if None"""
        if timeout is None:
            until = None
        else:
            until = time.time() + timeout

        if not isinstance(futures, list):
            futures = [futures]
        futures = [f for f in futures if not f.done()]

        while futures:
            self.log_debug("wait_all awaiting response ...")
            self._service_futures(futures, until)

    def _service_futures(self, futures, until=None):
        if until is None:
            timeout = None
        else:
            timeout = until - time.time()
            if timeout < 0:
                timeout = 0
        response = self.q.get(True, timeout)
        if response is Spawnable.STOP:
            self.log_debug("wait_all received Spawnable.STOP")
            raise StopIteration()
        self.log_debug("wait_all received response %s", response)
        if response.id in self._futures:
            f = self._update_future(response)
            if f in futures:
                futures.remove(f)
        elif response.id in self._subscriptions:
            result = self._invoke_callback(response)
            # Task's match_update callback returns a future if it has
            #  filled it (other callbacks not expected to return a val)
            if result in futures:
                futures.remove(result)
        else:
            self.log_debug("wait_all received unsolicited response")

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
        """called when a future is filled. Updates the future accordingly and
            removes it from the futures list"""
        self.log_debug("future %d filled", response.id)
        f = self._futures.pop(response.id)
        if isinstance(response, Error):
            f.set_exception(response.message)
            raise ValueError(response.message)
        elif isinstance(response, Return):
            f.set_result(response.value)
        else:
            raise ValueError(
                "Future received unexpected response: %s" % response)
        return f

    def _invoke_callback(self, response):
        self.log_debug("subscription %d callback", response.id)
        ret_val = None
        (endpoint, func, args) = self._subscriptions[response.id]
        if isinstance(response, Update):
            try:
                if func == match_update:
                    ret_val = func(response.value, *args)
                else:  # ignore return value from user callback functions
                    func(response.value, *args)
            except Exception as e:  # pylint:disable=broad-except
                # TODO: should we raise here?
                self.log_exception("Exception %s in callback %s" %
                                   (e, (endpoint, func, args)))
        elif isinstance(response, Error):
            raise RuntimeError(
                "Subscription received ERROR response: %s" % response)
        else:
            raise ValueError(
                "Subscription received unexpected response: %s" % response)
        return ret_val

    def define_spawn_function(self, func, *args):
        self._initialize()
        for spawned in self._spawned:
            assert spawned.ready(), "Spawned %r still running" % spawned
        self._spawn_functions = []
        self.add_spawn_function(
            func, self.make_default_stop_func(self.q), *args)

    def __del__(self):
        # Unsubscribe from anything that is still active
        ids = list(self._subscriptions)
        self.log_debug("Unsubscribing from ids %s", ids)
        for id_ in ids:
            self.unsubscribe(id_)
