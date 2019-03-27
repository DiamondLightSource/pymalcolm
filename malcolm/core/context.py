import weakref
import time

from annotypes import TYPE_CHECKING
import logging
import cothread

from .future import Future
from .request import Put, Post, Subscribe, Unsubscribe
from .response import Update, Return, Error
from .concurrency import Queue
from .errors import TimeoutError, AbortedError, BadValueError

if TYPE_CHECKING:
    from typing import Callable, Any, List, Union
    from .process import Process
    from .views import Block
    from .controller import Controller
    from .models import Model

# Create a module level logger
log = logging.getLogger(__name__)


class When(object):
    def __init__(self, good_value, bad_values):
        # type: (Callable[[Any], bool]) -> None
        if callable(good_value):
            def condition_satisfied(value):
                return good_value(value)
        else:
            def condition_satisfied(value):
                if bad_values and value in bad_values:
                    raise BadValueError(
                        "Waiting for %r, got %r" % (good_value, value))
                return value == good_value
            condition_satisfied.__name__ = "equals_%s" % good_value
        self.condition_satisfied = condition_satisfied
        self.future = None  # type: Future
        self.context = None  # type: Context
        self.last = None

    def set_future_context(self, future, context):
        # type: (Future, Context) -> None
        self.future = future
        self.context = context

    def __call__(self, value):
        # type: (Any) -> None
        # Need to check if we have a future as we might be called while the
        # unsubscribe is taking place
        if self.future:
            self.last = value
            try:
                satisfied = self.condition_satisfied(value)
            except Exception:
                # Bad value, so unsubscribe
                self.context.unsubscribe(self.future)
                self.future = None
                raise
            else:
                if satisfied:
                    # All done, so unsubscribe
                    self.context.unsubscribe(self.future)
                    self.future = None


class Context(object):
    """Helper allowing Future style access to Block Attributes and Methods"""

    STOP = object()

    def __init__(self, process):
        # type: (Process) -> None
        self._q = Queue()
        # Func to call just before requests are dispatched
        self._notify_dispatch_request = None
        self._notify_args = ()
        self._process = process
        self._next_id = 1
        self._futures = {}  # dict {int id: Future)}
        self._subscriptions = {}  # dict {int id: (func, args)}
        self._requests = {}  # dict {Future: Request}
        self._pending_unsubscribes = {}  # dict {Future: Subscribe}
        # If not None, wait for this before listening to STOPs
        self._sentinel_stop = None

    @property
    def mri_list(self):
        # type: () -> List[str]
        return self._process.mri_list

    def get_controller(self, mri):
        controller = self._process.get_controller(mri)
        return controller

    def block_view(self, mri):
        # type: (str) -> Block
        """Get a view of a block

        Args:
            mri: The mri of the controller hosting the block

        Returns:
            Block: The block we control
        """
        controller = self.get_controller(mri)
        block = controller.block_view(weakref.proxy(self))
        return block

    def make_view(self, controller, data, child_name):
        # type: (Controller, Model, str) -> Any
        return controller.make_view(self, data, child_name)

    def _get_next_id(self):
        new_id = self._next_id
        self._next_id += 1
        return new_id

    def set_notify_dispatch_request(self, notify_dispatch_request, *args):
        """Set function to call just before requests are dispatched

        Args:
            notify_dispatch_request (callable): function will be called
                with request as single arg just before request is dispatched
        """
        self._notify_dispatch_request = notify_dispatch_request
        self._notify_args = args

    def _dispatch_request(self, request):
        future = Future(weakref.proxy(self))
        self._futures[request.id] = future
        self._requests[future] = request
        controller = self.get_controller(request.path[0])
        if self._notify_dispatch_request:
            self._notify_dispatch_request(request, *self._notify_args)
        self.handle_request(controller, request)
        return future

    def handle_request(self, controller, request):
        controller.handle_request(request)
        # Yield control to allow the request to be handled
        cothread.Yield()

    def ignore_stops_before_now(self):
        """Ignore any stops received before this point"""
        self._sentinel_stop = object()
        self._q.put(self._sentinel_stop)

    def stop(self):
        """Stops any wait_all_futures call with an AbortedError"""
        self._q.put(self.STOP)

    def put(self, path, value, timeout=None, event_timeout=None):
        """"Puts a value to a path and returns when it completes

        Args:
            path (list): The path to put to
            value (object): The value to set
            timeout (float): time in seconds to wait for responses, wait forever
                if None
            event_timeout: maximum time in seconds to wait between each response
                event, wait forever if None

        Returns:
            The value after the put completes
        """
        future = self.put_async(path, value)
        self.wait_all_futures(
            future, timeout=timeout, event_timeout=event_timeout)
        return future.result()

    def put_async(self, path, value):
        """"Puts a value to a path and returns immediately

        Args:
            path (list): The path to put to
            value (object): The value to set

        Returns:
             Future: A single Future which will resolve to the result
        """
        request = Put(self._get_next_id(), path, value)
        request.set_callback(self._q.put)
        future = self._dispatch_request(request)
        return future

    def post(self, path, params=None, timeout=None, event_timeout=None):
        """Synchronously calls a method

        Args:
            path (list): The path to post to
            params (dict): parameters for the call
            timeout (float): time in seconds to wait for responses, wait
                forever if None
            event_timeout: maximum time in seconds to wait between each response
                event, wait forever if None

        Returns:
            the result from 'method'
        """
        future = self.post_async(path, params)
        self.wait_all_futures(
            future, timeout=timeout, event_timeout=event_timeout)
        return future.result()

    def post_async(self, path, params=None):
        """Asynchronously calls a function on a child block

        Args:
            path (list): The path to post to
            params (dict): parameters for the call

        Returns:
             Future: as single Future that will resolve to the result
        """
        request = Post(self._get_next_id(), path, params)
        request.set_callback(self._q.put)
        future = self._dispatch_request(request)
        return future

    def subscribe(self, path, callback, *args):
        """Subscribe to changes in a given attribute and call
        ``callback(future, value, *args)`` when it changes

        Returns:
            Future: A single Future which will resolve to the result
        """
        request = Subscribe(self._get_next_id(), path, delta=False)
        request.set_callback(self._q.put)
        # If self is in args, then make weak version of it
        saved_args = []
        for arg in args:
            if arg is self:
                saved_args.append(weakref.proxy(self))
            else:
                saved_args.append(arg)
        self._subscriptions[request.id] = (callback, saved_args)
        future = self._dispatch_request(request)
        return future

    def unsubscribe(self, future):
        """Terminates the subscription given by a future

        Args:
            future (Future): The future of the original subscription
        """
        assert future not in self._pending_unsubscribes, \
            "%r has already been unsubscribed from" % \
            self._pending_unsubscribes[future]
        subscribe = self._requests[future]
        self._pending_unsubscribes[future] = subscribe
        # Clear out the subscription
        self._subscriptions.pop(subscribe.id)
        request = Unsubscribe(subscribe.id)
        request.set_callback(self._q.put)
        try:
            controller = self.get_controller(subscribe.path[0])
        except ValueError:
            # Controller has already gone, probably during tearDown
            pass
        else:
            self.handle_request(controller, request)

    def unsubscribe_all(self, callback=False):
        """Send an unsubscribe for all active subscriptions"""
        futures = ((f, r) for f, r in self._requests.items()
                   if isinstance(r, Subscribe)
                   and f not in self._pending_unsubscribes)
        if futures:
            for future, request in futures:
                if callback:
                    log.warn("Unsubscribing from %s", request.path)
                    cothread.Callback(self.unsubscribe, future)
                else:
                    self.unsubscribe(future)

    def __del__(self):
        # Unsubscribe from anything that is still active
        self.unsubscribe_all(callback=True)

    def when_matches(self, path, good_value, bad_values=None, timeout=None,
                     event_timeout=None):
        """Resolve when an path value equals value

        Args:
            path (list): The path to wait to
            good_value (object): the value to wait for
            bad_values (list): values to raise an error on
            timeout (float): time in seconds to wait for responses, wait
                forever if None
            event_timeout: maximum time in seconds to wait between each response
                event, wait forever if None
        """
        future = self.when_matches_async(path, good_value, bad_values)
        self.wait_all_futures(
            future, timeout=timeout, event_timeout=event_timeout)

    def when_matches_async(self, path, good_value, bad_values=None):
        """Wait for an attribute to become a given value

        Args:
            path (list): The path to wait to
            good_value: If it is a callable then expect it to return
                True if we are satisfied and raise on error. If it is not
                callable then compare each value against this one and return
                if it matches.
            bad_values (list): values to raise an error on

        Returns:
            Future: a single Future that will resolve when the path matches
            good_value or bad_values
        """
        when = When(good_value, bad_values)
        future = self.subscribe(path, when)
        when.set_future_context(future, weakref.proxy(self))
        return future

    def wait_all_futures(self, futures, timeout=None, event_timeout=None):
        # type: (Union[List[Future], Future, None], float, float) -> None
        """Services all futures until the list 'futures' are all done
        then returns. Calls relevant subscription callbacks as they
        come off the queue and raises an exception on abort

        Args:
            futures: a `Future` or list of all futures that the caller
                wants to wait for
            timeout: maximum total time in seconds to wait for responses, wait
                forever if None
            event_timeout: maximum time in seconds to wait between each response
                event, wait forever if None
        """
        if timeout is None:
            end = None
        else:
            end = time.time() + timeout

        if not isinstance(futures, list):
            if futures:
                futures = [futures]
            else:
                futures = []

        filtered_futures = []

        for f in futures:
            if f.done():
                if f.exception() is not None:
                    raise f.exception()
            else:
                filtered_futures.append(f)

        while filtered_futures:
            if event_timeout is not None:
                until = time.time() + event_timeout
                if end is not None:
                    until = min(until, end)
            else:
                until = end
            self._service_futures(filtered_futures, until)

    def sleep(self, seconds):
        """Services all futures while waiting

        Args:
            seconds (float): Time to wait
        """
        until = time.time() + seconds
        try:
            while True:
                self._service_futures([], until)
        except TimeoutError:
            return

    def _describe_futures(self, futures):
        descriptions = []
        for future in futures:
            request = self._requests.get(future, None)
            if isinstance(request, Put):
                path = ".".join(request.path)
                descriptions.append("%s.put_value(%s)" % (path, request.value))
            elif isinstance(request, Subscribe):
                path = ".".join(request.path)
                func, _ = self._subscriptions.get(request.id, (None, None))
                if isinstance(func, When):
                    descriptions.append("When(%s, %s, last=%s)" % (
                        path, func.condition_satisfied.__name__, func.last))
                elif func is None:
                    # We have already called unsubscribe, but haven't received
                    # the Return for it yet
                    descriptions.append("Unsubscribed(%s)" % path)
                else:
                    descriptions.append("Subscribe(%s)" % path)
            elif isinstance(request, Post):
                path = ".".join(request.path)
                if request.parameters:
                    params = "..."
                else:
                    params = ""
                descriptions.append("%s(%s)" % (path, params))
            else:
                descriptions.append(str(request))
        if descriptions:
            return "[" + ", ".join(descriptions) + "]"
        else:
            return "[]"

    def _service_futures(self, futures, until=None):
        """Args:
            futures (list): The futures to service
            until (float): Timestamp to wait until
        """
        if until is None:
            timeout = None
        else:
            timeout = until - time.time()
            if timeout < 0:
                timeout = 0
        try:
            response = self._q.get(timeout)
        except TimeoutError:
            raise TimeoutError(
                "Timeout waiting for %s" % self._describe_futures(futures))
        if response is self._sentinel_stop:
            self._sentinel_stop = None
        elif response is self.STOP:
            if self._sentinel_stop is None:
                # This is a stop we should listen to...
                raise AbortedError(
                    "Aborted waiting for %s" % self._describe_futures(futures))
        elif isinstance(response, Update):
            # This is an update for a subscription
            if response.id in self._subscriptions:
                func, args = self._subscriptions[response.id]
                func(response.value, *args)
        elif isinstance(response, Return):
            future = self._futures.pop(response.id)
            del self._requests[future]
            self._pending_unsubscribes.pop(future, None)
            result = response.value
            future.set_result(result)
            try:
                futures.remove(future)
            except ValueError:
                pass
        elif isinstance(response, Error):
            future = self._futures.pop(response.id)
            del self._requests[future]
            future.set_exception(response.message)
            try:
                futures.remove(future)
            except ValueError:
                pass
            else:
                raise response.message
