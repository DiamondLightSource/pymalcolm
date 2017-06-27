from .view import View


class Method(View):
    """Exposes a function with metadata for arguments and return values"""

    def __init__(self, controller, context, data):
        self._do_init(controller, context, data)

    def _add_positional_args(self, args, kwargs):
        # add any positional args into our kwargs dict
        for name, v in zip(self._data.takes.elements, args):
            assert name not in kwargs, \
                "%s specified as positional and keyword args" % (name,)
            kwargs[name] = v
        return kwargs

    def post(self, *args, **kwargs):
        kwargs = self._add_positional_args(args, kwargs)
        result = self._context.post(self._data.path, kwargs)
        return result

    __call__ = post

    def post_async(self, *args, **kwargs):
        kwargs = self._add_positional_args(args, kwargs)
        fs = self._context.post_async(self._data.path, kwargs)
        return fs

    @property
    def takes(self):
        return self._controller.make_view(self._context, self._data, "takes")

    @property
    def defaults(self):
        return self._controller.make_view(self._context, self._data, "defaults")

    @property
    def description(self):
        return self._controller.make_view(
            self._context, self._data, "description")

    @property
    def tags(self):
        return self._controller.make_view(self._context, self._data, "tags")

    @property
    def writeable(self):
        return self._controller.make_view(
            self._context, self._data, "writeable")

    @property
    def label(self):
        return self._controller.make_view(self._context, self._data, "label")

    @property
    def returns(self):
        return self._controller.make_view(self._context, self._data, "returns")
