from collections import OrderedDict

from malcolm.compat import str_


class Cache(OrderedDict):
    """OrderedDict subclass that supports delta changeset updates"""

    def apply_changes(self, *changes):
        """Update dictionary from the given delta

        Args:
            changes (list): where each change is [path, update] for an addition
                or change, and [path] for deletion. path is a tuple of paths
                within the dictionary to change, and update is the value that it
                should be updated to
        """
        for change in changes:
            d = self
            assert len(change) in (1, 2), \
                "Expected [path] for deletion or [path, update] for addition." \
                " Got %s" % (change,)
            path = change[0]
            if len(path) == 0:
                # Replace cache with value
                self.clear()
                if len(change) > 1:
                    value = change[1]
                    self.update(value)
            else:
                assert isinstance(path[0], str_), \
                    "Expected string as first element of path, got %s" % (path[0])
                d = self.walk_path(path[:-1])
                if len(change) == 1:
                    # deletion
                    del d[path[-1]]
                else:
                    # addition or change
                    value = change[1]
                    d[path[-1]] = value

    def walk_path(self, path):
        """Walk the path, and return the given endpoint"""
        d = self
        for p in path:
            d = d[p]
        return d
