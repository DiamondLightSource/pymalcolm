from collections import OrderedDict


class Cache(OrderedDict):
    """OrderedDict subclass that supports delta changeset updates"""

    def delta_update(self, delta):
        """Update dictionary from the given delta

        Args:
            delta (list): where delta is [path, update] for an addition or
                change, and [path] for deletion. path is a tuple of paths within
                the dictionary to change, and update is the value that it should
                be updated to
        """
        d = self
        assert len(delta) in (1, 2), \
            "Expected [path] for deletion or [path, update] for addition. " \
            "Got %s" % (delta,)
        path = delta[0]
        assert len(path) > 0, \
            "Expected path to be a non-empty list, got %s" % (path,)
        d = self.walk_path(path[:-1])
        if len(delta) == 1:
            # deletion
            del d[path[-1]]
        else:
            # addition or change
            value = delta[1]
            d[path[-1]] = value

    def walk_path(self, path):
        """Walk the path, and return the given endpoint"""
        d = self
        for p in path:
            d = d[p]
        return d
