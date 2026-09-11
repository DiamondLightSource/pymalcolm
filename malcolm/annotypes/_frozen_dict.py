def not_supported(self, *args, **kwargs):
    raise TypeError("FrozenOrderedDict is immutable")


class FrozenOrderedDict(dict):
    """Absolutely minimal implementation of an OrderedDict, frozen at init to
    give better performance than the one in collections"""
    def __init__(self, seq=()):
        super(FrozenOrderedDict, self).__init__()
        keys = []
        setitem = super(FrozenOrderedDict, self).__setitem__
        append = keys.append
        for k, v in seq:
            setitem(k, v)
            append(k)
        self._keys = keys

    __setitem__ = not_supported
    __delitem__ = not_supported

    def __iter__(self):
        return (k for k in self._keys)

    clear = not_supported
    copy = not_supported

    def items(self):
        return [(k, self[k]) for k in self._keys]

    def iteritems(self):
        return ((k, self[k]) for k in self._keys)

    iterkeys = __iter__

    def itervalues(self):
        return (self[k] for k in self._keys)

    def keys(self):
        return self._keys

    pop = not_supported
    popitem = not_supported
    setdefault = not_supported
    update = not_supported

    def values(self):
        return [self[k] for k in self._keys]

    viewitems = not_supported
    viewkeys = not_supported
    viewvalues = not_supported
