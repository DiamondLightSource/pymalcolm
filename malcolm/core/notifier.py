from contextlib import contextmanager

from annotypes import TYPE_CHECKING, FrozenOrderedDict, Array

from .loggable import Loggable
from .request import Subscribe, Unsubscribe
from .response import Response
from .concurrency import RLock

if TYPE_CHECKING:
    from .models import BlockModel
    from typing import List, Tuple, Callable, Any, Dict
    Callback = Callable[[Response], None]
    CallbackResponses = List[Tuple[Callback, Response]]
    SubscriptionKeys = Dict[Tuple[Callback, int], Subscribe]


class DummyNotifier(object):
    @property
    @contextmanager
    def changes_squashed(self):
        yield

    def add_squashed_change(self, path, data):
        # type: (List[str], Any) -> None
        pass

    def add_squashed_delete(self, path):
        # type: (List[str]) -> None
        pass


def freeze(o):
    # Cheaper than a subclass check, will find Models for us and freeze them
    # into dicts
    if hasattr(o, "notifier"):
        o = FrozenOrderedDict((("typeid", o.typeid),) + tuple(
            (k, freeze(getattr(o, k)))
            for k in o.call_types
        ))
    elif isinstance(o, dict):
        # Recurse down in case there are any models down there
        o = FrozenOrderedDict(tuple((k, freeze(v)) for k, v in o.items()))
    elif o.__class__ is Array and hasattr(o.typ, "notifier"):
        # Recurse down only if the type suggests it has a model
        o = [freeze(v) for v in o.seq]
    return o


class Notifier(Loggable):
    """Object that can service callbacks on given endpoints"""

    def __init__(self, mri, lock, block):
        # type: (str, RLock, BlockModel) -> None
        self.set_logger(mri=mri)
        self._tree = NotifierNode(block)
        self._lock = lock
        # Incremented every time we do with changes_squashed
        self._squashed_count = 0
        self._squashed_changes = []  # type: List[List]
        self._subscription_keys = {}  # type: SubscriptionKeys

    def handle_subscribe(self, request):
        # type: (Subscribe) -> CallbackResponses
        """Handle a Subscribe request from outside. Called with lock taken"""
        ret = self._tree.handle_subscribe(request, request.path[1:])
        self._subscription_keys[request.generate_key()] = request
        return ret

    def handle_unsubscribe(self, request):
        # type: (Unsubscribe) -> CallbackResponses
        """Handle a Unsubscribe request from outside. Called with lock taken"""
        subscribe = self._subscription_keys.pop(request.generate_key())
        ret = self._tree.handle_unsubscribe(subscribe, subscribe.path[1:])
        return ret

    @property
    def changes_squashed(self):
        # type: () -> Notifier
        """Context manager to allow multiple calls to notify_change() to be
        made and all changes squashed into one consistent set. E.g:

        with notifier.changes_squashed:
            attr.set_value(1)
            attr.set_alarm(MINOR)
        """
        return self

    def add_squashed_change(self, path, data):
        # type: (List[str], Any) -> None
        """Register a squashed change to a particular path

        Args:
            path (list): The path of what has changed, relative from Block
            data (object): The new data
        """
        assert self._squashed_count, "Called while not squashing changes"
        self._squashed_changes.append([path[1:], data])

    def add_squashed_delete(self, path):
        # type: (List[str]) -> None
        """Register a squashed deletion of a particular path

        Args:
            path (list): The path of what has changed, relative from Block
        """
        assert self._squashed_count, "Called while not squashing changes"
        self._squashed_changes.append([path[1:]])

    def __enter__(self):
        """So we can use this as a context manager for squashing changes"""
        self._lock.acquire()
        self._squashed_count += 1

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        """So we can use this as a context manager for squashing changes"""
        responses = []
        try:
            self._squashed_count -= 1
            if self._squashed_count == 0:
                changes = self._squashed_changes
                self._squashed_changes = []
                # TODO: squash intermediate deltas here?
                responses += self._tree.notify_changes(changes)
        finally:
            self._lock.release()
            self._callback_responses(responses)

    def _callback_responses(self, responses):
        # type: (CallbackResponses) -> None
        for cb, response in responses:
            try:
                cb(response)
            except Exception:
                self.log.exception("Exception notifying %s", response)
                raise


class NotifierNode(object):

    # Define slots so it uses less resources to make these
    __slots__ = [
        "delta_requests", "update_requests", "children", "parent", "data"]

    def __init__(self, data, parent=None):
        # type: (Any, NotifierNode) -> None
        self.delta_requests = []  # type: List[Subscribe]
        self.update_requests = []  # type: List[Subscribe]
        self.children = {}  # type: Dict[str, NotifierNode]
        self.parent = parent
        self.data = data

    def notify_changes(self, changes):
        # type: (List[List]) -> CallbackResponses
        """Set our data and notify anyone listening

        Args:
            changes (list): [[path, optional data]] where path is the path to
                what has changed, and data is the unserialized object that has
                changed

        Returns:
            list: [(callback, Response)] that need to be called
        """
        ret = []
        child_changes = {}
        for change in changes:
            # Add any changes that our children need to know about
            self._add_child_change(change, child_changes)

        # If we have update subscribers, freeze at this level
        if self.update_requests:
            frozen = freeze(self.data)
            for request in self.update_requests:
                ret.append(request.update_response(frozen))

        # If we have delta subscribers, freeze the change value
        if self.delta_requests:
            for change in changes:
                change[-1] = freeze(change[-1])
            for request in self.delta_requests:
                ret.append(request.delta_response(changes))

        # Now notify our children
        for name, child_changes in child_changes.items():
            ret += self.children[name].notify_changes(child_changes)
        return ret

    def _add_child_change(self, change, child_changes):
        # type: (List, Dict[str, List]) -> None
        path = change[0]
        if path:
            # This is for one of our children
            name = path[0]
            if name in self.children:
                if len(change) == 2:
                    child_change = [path[1:], change[1]]
                else:
                    child_change = [path[1:]]
                child_changes.setdefault(name, []).append(child_change)
        else:
            # This is for us
            if len(change) == 2:
                child_change_dict = self._update_data(change[1])
            else:
                child_change_dict = self._update_data(None)
            for name, child_change in child_change_dict.items():
                child_changes.setdefault(name, []).append(child_change)

    def _update_data(self, data):
        # type: (Any) -> Dict[str, List]
        """Set our data and notify any subscribers of children what has changed

        Args:
            data (object): The new data

        Returns:
            dict: {child_name: [path_list, optional child_data]} of the change
                that needs to be passed to a child as a result of this
        """
        self.data = data
        child_change_dict = {}
        # Reflect change of data to children
        for name in self.children:
            child_data = getattr(data, name, None)
            if child_data is None:
                # Deletion
                child_change_dict[name] = [[]]
            else:
                # Change
                child_change_dict[name] = [[], child_data]
        return child_change_dict

    def handle_subscribe(self, request, path):
        # type: (Subscribe, List[str]) -> CallbackResponses
        """Add to the list of request to notify, and notify the initial value of
        the data held

        Args:
            request (Subscribe): The subscribe request
            path (list): The relative path from ourself

        Returns:
            list: [(callback, Response)] that need to be called
        """
        ret = []
        if path:
            # Recurse down
            name = path[0]
            if name not in self.children:
                self.children[name] = NotifierNode(
                    getattr(self.data, name, None), self)
            ret += self.children[name].handle_subscribe(request, path[1:])
        else:
            # This is for us
            frozen = freeze(self.data)
            if request.delta:
                self.delta_requests.append(request)
                ret.append(request.delta_response([[[], frozen]]))
            else:
                self.update_requests.append(request)
                ret.append(request.update_response(frozen))
        return ret

    def handle_unsubscribe(self, request, path):
        # type: (Subscribe, List[str]) -> CallbackResponses
        """Remove from the notifier list and send a return

        Args:
            request (Subscribe): The original subscribe request
            path (list): The relative path from ourself

        Returns:
            list: [(callback, Response)] that need to be called
        """
        ret = []
        if path:
            # Recurse down
            name = path[0]
            child = self.children[name]
            ret += child.handle_unsubscribe(request, path[1:])
            if not child.children and not child.update_requests \
                    and not child.delta_requests:
                del self.children[name]
        else:
            # This is for us
            if request in self.update_requests:
                self.update_requests.remove(request)
            else:
                self.delta_requests.remove(request)
            ret.append(request.return_response())
        return ret
