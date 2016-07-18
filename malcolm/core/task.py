from malcolm.core.loggable import Loggable
from malcolm.core.future import Future
from malcolm.core.attribute import Attribute
from malcolm.core.request import Request, Subscribe, Unsubscribe, Post
from malcolm.core.response import Response, Error, Delta, Return, Update


class Task(Loggable):
    """Provides a mechanism for executing commands and setting or monitoring
        attributes on blocks. Note that queue handling is executed in the
        caller's thread (by calling wait_all). Hence this module is not
        thread safe"""
    # TODO: when Task object is destroyed  we need to cancel all subscriptions
    # Sentinel object that when received stops the recv_loop
    TASK_STOP = object()

    def __init__(self, name, process):
        self.set_logger_name(name)
        self.name = name
        self.process = process
        self.q = self.process.create_queue()
        self._next_id = 0
        self._futures = {}  # dict {int id: Future}
        self._subscriptions = {}  # dict  {int id: (endpoint, func, args)}

    def _save_future(self, future):
        """ stores the future with unique id"""
        new_id = self._next_id
        self._next_id += 1
        self._futures[new_id] = future
        return new_id

    def _save_subscription(self, endpoint, function, *args):
        """ stores a subscription with unique id"""
        new_id = self._next_id
        self._next_id += 1
        self._subscriptions[new_id] = (endpoint, function, args)
        return new_id

    def put(self, attr_or_items, value=None):
        """"puts a value or values into an attribute or attributes and returns
                once all values have been set

            Args:
                attr_or_items (Attribute or Dict): The attribute or dictionary
                    of {attributes: values} to set
                value (object): For single attr, the value set

            Returns:
                 a list of futures to monitor when each put completes"""
        f = self.put_async(attr_or_items, value)
        self.wait_all(f)

    def put_async(self, attr_or_items, value=None):
        """"puts a value or values into an attribute or attributes and returns
            immediately

            Args:
                attr_or_items (Attribute or Dict): The attribute or dictionary
                    of {attributes: values} to set
                value (object): For single attr, the value set

            Returns:
                 a list of futures to monitor when each put completes"""
        if value:
            attr_or_items = {attr_or_items: value}
        result_f = []

        for attr, value in attr_or_items.items():
            endpoint = [attr.parent.name, attr.name, "value"]
            request = Post(None, self.q, endpoint, value)
            f = Future(self)
            new_id = self._save_future(f)
            request.set_id(new_id)
            self.process.q.put(request)
            result_f.append(f)

        return result_f

    def _match_update(self, value, future, required_value, subscription_ids):
        """a callback for monitoring 'when_matches' requests"""
        self.log_debug("_match_update callback fired")

        ret_val = None
        if value == required_value:
            self.log_debug("_match_update got a match")
            future.set_result(value)
            self.unsubscribe(subscription_ids[0])
            # future returned to wait_all - to be removed from wait list
            ret_val = future
        return ret_val

    def when_matches(self, attr, value):
        """ Wait for an attribute to become a given value

            Args:
                attr (Attribute): The attribute to wait for
                value (object): the value to wait for

            Returns: a list of one futures which will complete when
                all attribute values match the input"""

        f = Future(self)
        self._save_future(f)
        subscription_ids = []
        subscription_id = self.subscribe(
            attr, self._match_update, f, value, subscription_ids)
        subscription_ids.append(subscription_id)

        return [f]

    def post(self, method, params):
        """Synchronously calls a block method

            Args:
                method (Method): the method to call
                params (dict): parameters for the call

            Returns:
                the result from 'method'"""

        f = self.post_async(method, params)
        self.wait_all(f)

        return f

    def post_async(self, method, params):
        """Asynchronously calls a function on a child block

            Returns a list of one future which will proved the return value
            on completion"""
        endpoint = [method.parent.name, method.name]
        request = Post(None, self.q, endpoint, params)
        f = Future(self)
        new_id = self._save_future(f)
        request.set_id(new_id)
        self.process.q.put(request)

        return [f]

    def subscribe(self, attr, callback, *args):
        """subscribe to changes in a given attribute and call callback
            with (*args) when it changes

            Returns an id for the subscription"""

        endpoint = [attr.parent.name, attr.name]
        request = Subscribe(None, self.q, endpoint, False)
        new_id = self._save_subscription(endpoint, callback, *args)
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


    def stop(self):
        """Puts an abort on the queue"""
        self.q.put(Task.TASK_STOP)

    def wait_all(self, futures, timeout=None):
        """services all futures until the list 'futures' are all done
            then returns. Calls relevant subscription callbacks as they
            come off the queue and raises an exception on abort

            Args:
                futures ([Future] or Future): a future or list of all futures
                    that the caller wants to wait for
                timeout (Float) time in seconds to wait for responses, wait
                    forever if None"""
        if not isinstance(futures, list):
            futures = [futures]

        futures = [f for f in futures if not f.done()]

        while futures:
            self.log_debug("wait_all awaiting response ...")
            response = self.q.get(True, timeout)
            self.log_debug("wait_all received response %s", response)
            if response is Task.TASK_STOP:
                raise RuntimeWarning("Task aborted")
            elif response.id_ in self._futures:
                f = self._update_future(response)
                if f in futures:
                    futures.remove(f)
            elif response.id_ in self._subscriptions:
                result = self._invoke_callback(response)
                # Task's _match_update callback returns a future if it has
                #  filled it (other callbacks not expected to return a val)
                if result in futures:
                    futures.remove(result)
            else:
                self.log_debug("wait_all recieved unsolcited response")

    def _update_future(self, response):
        """called when a future is filled. Updates the future accordingly and
            removes it from the futures list"""
        self.log_debug("future %d filled", response.id_)
        f = self._futures.pop(response.id_)
        if isinstance(response, Error):
            f.set_exception(response.message)
        elif isinstance(response, Return):
            f.set_result(response.value)
        else:
            raise ValueError(
                "Future received unexpected response: %s" % response)
        return f

    def _invoke_callback(self, response):
        self.log_debug("subscription %d callback", response.id_)
        ret_val = None
        (endpoint, func, args) = self._subscriptions[response.id_]
        if isinstance(response, Update):
            try:
                if func == self._match_update:
                    ret_val = func(response.value, *args)
                else: # ignore return value from user callback functions
                    func(response.value, *args)
            except Exception as e:
                self.log_exception("Exception %s in callback %s" %
                                   (e, (func, args)))
        elif isinstance(response, Error):
            raise RuntimeError(
                "Subscription received ERROR response: %s" % response)
        else:
            raise ValueError(
                "Subscription received unexpected response: %s" % response)
        return ret_val
