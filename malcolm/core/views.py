from annotypes import TYPE_CHECKING

from malcolm.compat import OrderedDict
from .context import Context
from .models import BlockModel, MethodModel, AttributeModel
from malcolm.core.models import Model

if TYPE_CHECKING:
    from typing import Any
    from .controller import Controller


class View(object):
    """View of a Model to allow Put, Get, Subscribe etc."""
    _controller = None  # type: Controller
    _context = None  # type: Context
    _data = None  # type: Model
    typeid = None  # type: str

    def __init__(self, controller, context, data):
        # type: (Controller, Context, Model) -> None
        object.__setattr__(self, "typeid", data.typeid)
        object.__setattr__(self, "_controller", controller)
        object.__setattr__(self, "_context", context)
        object.__setattr__(self, "_data", data)

    def __iter__(self):
        return iter(self._data)

    def to_dict(self):
        return self._data.to_dict()

    def __getitem__(self, item):
        try:
            return getattr(self, item)
        except AttributeError:
            return KeyError(item)

    def __setattr__(self, name, value):
        raise NameError("Cannot set attribute %s on view" % name)


def _make_get_property(cls, endpoint):
    @property
    def make_child_view(self):
        # Get the child of self._data. Needs to be done by the controller to
        # make sure lock is taken and we get consistent data
        child = self._context.make_view(self._controller, self._data, endpoint)
        return child

    setattr(cls, endpoint, make_child_view)


def _make_view_subclass(cls, controller, context, data):
    # Properties can only be set on classes, so make subclass that we can use
    class ViewSubclass(cls):
        pass

    for endpoint in data:
        # make properties for the endpoints we know about
        _make_get_property(ViewSubclass, endpoint)

    view = ViewSubclass(controller, context, data)
    return view


class Attribute(View):
    """Represents a value with type information that may be backed elsewhere"""

    @property
    def meta(self):
        return self._context.make_view(self._controller, self._data, "meta")

    @property
    def value(self):
        return self._context.make_view(self._controller, self._data, "value")

    def put_value(self, value, timeout=None):
        """Put a value to the Attribute and wait for completion"""
        self._context.put(self._data.path + ["value"], value, timeout=timeout)

    def put_value_async(self, value):
        fs = self._context.put_async(self._data.path + ["value"], value)
        return fs

    def subscribe_value(self, callback, *args):
        return self._context.subscribe(
            self._data.path + ["value"], callback, *args)

    @property
    def alarm(self):
        return self._context.make_view(self._controller, self._data, "alarm")

    # noinspection PyPep8Naming
    # timeStamp is camelCase to maintain compatibility with EPICS normative
    # types
    @property
    def timeStamp(self):
        return self._context.make_view(
            self._controller, self._data, "timeStamp")

    def __repr__(self):
        return "<%s value=%r>" % (self.__class__.__name__, self.value)


class Method(View):
    """Exposes a function with metadata for arguments and return values"""

    def _add_positional_args(self, args, kwargs):
        # add any positional args into our kwargs dict
        for name, v in zip(self._data.meta.takes.elements, args):
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
    def meta(self):
        return self._context.make_view(self._controller, self._data, "meta")

    @property
    def took(self):
        return self._context.make_view(self._controller, self._data, "took")

    @property
    def returned(self):
        return self._context.make_view(self._controller, self._data, "returned")


class Block(View):
    """Object consisting of a number of Attributes and Methods"""
    def __init__(self, controller, context, data):
        super(Block, self).__init__(controller, context, data)
        for endpoint in self._data:
            if isinstance(data[endpoint], MethodModel):
                # Add _async versions of method
                self._make_async_method(endpoint)

    def __getattr__(self, item):
        # type: (str) -> View
        # Get the child of self._data. Needs to be done by the controller to
        # make sure lock is taken and we get consistent data
        child = self._context.make_view(self._controller, self._data, item)
        return child

    @property
    def mri(self):
        return self._data.path[0]

    def _make_async_method(self, endpoint):
        def post_async(*args, **kwargs):
            child = getattr(self, endpoint)  # type: Method
            return child.post_async(*args, **kwargs)

        object.__setattr__(self, "%s_async" % endpoint, post_async)

    def put_attribute_values_async(self, params):
        futures = []
        if type(params) is dict:
            # If we have a plain dictionary, then sort items
            items = sorted(params.items())
        else:
            # Assume we are already ordered
            items = params.items()
        for attr, value in items:
            assert hasattr(self, attr), \
                "Block does not have attribute %s" % attr
            future = self._context.put_async(
                self._data.path + [attr, "value"], value)
            futures.append(future)
        return futures

    def put_attribute_values(self, params, timeout=None, event_timeout=None):
        futures = self.put_attribute_values_async(params)
        self._context.wait_all_futures(
            futures, timeout=timeout, event_timeout=event_timeout)

    def when_value_matches(self, attr, good_value, bad_values=None,
                           timeout=None, event_timeout=None):
        future = self.when_value_matches_async(attr, good_value, bad_values)
        self._context.wait_all_futures(
            future, timeout=timeout, event_timeout=event_timeout)

    def when_value_matches_async(self, attr, good_value, bad_values=None):
        path = self._data.path + [attr, "value"]
        future = self._context.when_matches_async(path, good_value, bad_values)
        return future


def make_view(controller, context, data):
    # type: (Controller, Context, Any) -> Any
    """Make a View subclass containing properties specific for given data

    Args:
        controller (Controller): The child controller that hosts the data
        context (Context): The context the parent has made that the View should
            use for manipulating the data
        data (Model): The actual data that context will be manipulating

    Returns:
        View: A View subclass instance that provides a user-focused API to
            the given data
    """
    if isinstance(data, BlockModel):
        # Make an Block View
        view = _make_view_subclass(Block, controller, context, data)
    elif isinstance(data, AttributeModel):
        # Make an Attribute View
        view = Attribute(controller, context, data)
    elif isinstance(data, MethodModel):
        # Make a Method View
        view = Method(controller, context, data)
    elif isinstance(data, Model):
        # Make a generic View
        view = _make_view_subclass(View, controller, context, data)
    elif isinstance(data, dict):
        # Make a dict of Views
        d = OrderedDict()
        for k, v in data.items():
            d[k] = make_view(controller, context, v)
        view = d
    elif isinstance(data, list):
        # Need to recurse down
        view = [make_view(controller, context, x) for x in data]
    else:
        # Just return the data unwrapped as it should be immutable
        view = data
    return view
