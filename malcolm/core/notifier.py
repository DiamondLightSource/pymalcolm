from .serializable import serialize_object
from .loggable import Loggable
from .request import Subscribe, Unsubscribe


class Notifier(Loggable):
    """Object that can service callbacks on given endpoints"""

    def __init__(self, mri, lock, block):
        super(Notifier, self).__init__(mri=mri)
        self._tree = NotifierNode(block)
        self._lock = lock
        # Incremented every time we do with changes_squashed
        self._squashed_count = 0
        self._squashed_changes = []
        # {Subscribe.generator_key(): Subscribe}
        self._subscription_keys = {}

    def handle_subscribe(self, request):
        """Handle a Subscribe request from outside. Called with lock taken

        Args:
            request (Subscribe): Request to respond to

        Returns:
            list: [(callback, Response)] that need to be called
        """
        ret = self._tree.handle_subscribe(request, request.path[1:])
        self._subscription_keys[request.generate_key()] = request
        return ret

    def handle_unsubscribe(self, request):
        """Handle a Unsubscribe request from outside. Called with lock taken

        Args:
            request (Unsubscribe): Request to respond to

        Returns:
            list: [(callback, Response)] that need to be called
        """
        subscribe = self._subscription_keys.pop(request.generate_key())
        ret = self._tree.handle_unsubscribe(subscribe, subscribe.path[1:])
        return ret

    @property
    def changes_squashed(self):
        """Context manager to allow multiple calls to notify_change() to be
        made and all changes squashed into one consistent set. E.g:

        with notifier.changes_squashed:
            attr.set_value(1)
            attr.set_alarm(MINOR)
        """
        return self

    def add_squashed_change(self, path, data=None):
        """Call setter, then notify subscribers of change

        Args:
            path (list): The path of what has changed, relative from Block
            data (object): The new data, None for deletion
        """
        assert self._squashed_count, "Called while not squashing changes"
        if data is None:
            change = [path[1:]]
        else:
            change = [path[1:], data]
        self._squashed_changes.append(change)

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
                # TODO: squash intermediate changes here?
                responses += self._tree.notify_changes(changes)
        finally:
            self._lock.release()
            self._callback_responses(responses)

    def _callback_responses(self, responses):
        for cb, response in responses:
            try:
                cb(response)
            except Exception:
                self.log.exception("Exception notifying %s", response)


class NotifierNode(object):

    # Define slots so it uses less resources to make these
    __slots__ = [
        "delta_requests", "update_requests", "children", "parent", "data"]

    def __init__(self, data, parent=None):
        # [Subscribe]
        self.delta_requests = []
        self.update_requests = []
        # {name: NotifierNode}
        self.children = {}
        # Leaf
        self.parent = parent
        # object
        self.data = data

    def notify_changes(self, changes):
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

        # If we have update subscribers, serialize at this level
        if self.update_requests:
            serialized = serialize_object(self.data)
            for request in self.update_requests:
                ret.append(request.update_response(serialized))

        # If we have delta subscribers, serialize the changes
        if self.delta_requests:
            for change in changes:
                change[-1] = serialize_object(change[-1])
            for request in self.delta_requests:
                ret.append(request.delta_response(changes))

        # Now notify our children
        for name, child_changes in child_changes.items():
            ret += self.children[name].notify_changes(child_changes)
        return ret

    def _add_child_change(self, change, child_changes):
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
            serialized = serialize_object(self.data)
            if request.delta:
                self.delta_requests.append(request)
                ret.append(request.delta_response([[[], serialized]]))
            else:
                self.update_requests.append(request)
                ret.append(request.update_response(serialized))
        return ret

    def handle_unsubscribe(self, request, path):
        """Remove from the notifier list and send a return

        Args:
            request (Subscribe): The original subscribe request

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