from malcolm.compat import OrderedDict, str_


class Leaf(object):
    def __init__(self, parent=None):
        self.subscriptions = []
        # {name: Leaf}
        self.children = {}
        self.parent = parent


EmptyLeaf = Leaf()


class Cache(OrderedDict):
    """OrderedDict subclass that supports delta changeset updates"""
    _subscription_tree = None

    def apply_changes(self, *changes):
        """Update dictionary from the given delta

        Args:
            changes (list): where each change is [path, update] for an addition
                or change, and [path] for deletion. path is a tuple of paths
                within the dictionary to change, and update is the value that it
                should be updated to
        """
        # {subscriber: [change]}
        subscription_changes = OrderedDict()
        for change in changes:
            assert len(change) in (1, 2), \
                "Expected [path] for deletion or [path, update] for addition." \
                " Got %s" % (change,)
            path = change[0]
            if len(path) == 0:
                # Replace cache with value
                self.clear()
                if len(change) > 1:
                    value = change[1]
                    for k, v in value.items():
                        self[k] = v
                self._notify_change(subscription_changes, change)
            else:
                assert isinstance(path[0], str_), \
                    "Expected path to be list of strings, got %s" % (path,)
                d = self.walk_path(path[:-1])
                if len(change) == 1:
                    # deletion
                    del d[path[-1]]
                    # TODO: how to subscribe here?
                else:
                    # addition or change
                    value = change[1]
                    d[path[-1]] = value
                    self._notify_change(subscription_changes, change)
        return subscription_changes

    def walk_path(self, path):
        """Walk the path, and return the given endpoint"""
        d = self
        for p in path:
            d = d[p]
        return d

    def _add_changes(self, subscription_changes, leaf, change, i=0):
        if leaf.subscriptions:
            if i:
                change = [change[0][i:]] + change[1:]
            for subscription in leaf.subscriptions:
                subscription_changes.setdefault(subscription, []).append(change)

    def _notify_change(self, subscription_changes, change):
        if self._subscription_tree is None:
            return
        leaf = self._subscription_tree
        self._add_changes(subscription_changes, leaf, change)
        for i, node in enumerate(change[0]):
            leaf = leaf.children.get(node, EmptyLeaf)
            self._add_changes(subscription_changes, leaf, change, i + 1)

        # Anyone downstream of this leaf needs notifying
        self._notify_sub_leaves(subscription_changes, leaf, change[1])

    def _notify_sub_leaves(self, subscription_changes, leaf, d):
        for node, leaf in leaf.children.items():
            change = [[], d[node]]
            self._add_changes(subscription_changes, leaf, change)
            self._notify_sub_leaves(subscription_changes, leaf, d[node])

    def _find_leaf(self, path):
        leaf = self._subscription_tree
        for node in path:
            if node not in leaf.children:
                leaf.children[node] = Leaf(leaf)
            leaf = leaf.children[node]
        return leaf

    def add_subscriber(self, subscription, path):
        if self._subscription_tree is None:
            self._subscription_tree = Leaf()
        leaf = self._find_leaf(path)
        leaf.subscriptions.append(subscription)

    def remove_subscriber(self, subscription, path):
        leaf = self._find_leaf(path)
        leaf.subscriptions.remove(subscription)
        while leaf.parent and not leaf.subscriptions and not leaf.children:
            node_name = [k for (k, v) in leaf.parent.children.items()
                         if v == leaf][0]
            leaf.parent.children.pop(node_name)
            leaf = leaf.parent

