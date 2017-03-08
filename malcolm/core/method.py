from .view import View


class Method(View):
    """Exposes a function with metadata for arguments and return values"""

    def _add_positional_args(self, args, kwargs):
        # add any positional args into our kwargs dict
        for name, v in zip(self._data.takes.elements, args):
            assert name not in kwargs, \
                "%s specified as positional and keyword args" % (name,)
            kwargs[name] = v
        return kwargs

    def post(self, *args, **kwargs):
        kwargs = self._add_positional_args(args, kwargs)
        self._context.post(self._data.path, kwargs)

    __call__ = post

    def post_async(self, *args, **kwargs):
        kwargs = self._add_positional_args(args, kwargs)
        fs = self._context.post_async(self._data.path, kwargs)
        return fs
