from .methodmodel import MethodModel
from .view import View, make_get_property


class Block(View):
    """Object consisting of a number of Attributes and Methods"""
    @property
    def mri(self):
        return self._data.path[0]

    def _prepare_endpoints(self, data):
        for endpoint in data:
            if isinstance(data[endpoint], MethodModel):
                # Add _async versions of method
                self._make_async_method(endpoint)
        return super(Block, self)._prepare_endpoints(data)

    def _make_async_method(self, endpoint):
        def post_async(*args, **kwargs):
            child = getattr(self, endpoint)
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

    def wait_all_futures(self, futures, timeout=None, event_timeout=None):
        self._context.wait_all_futures(
            futures, timeout=timeout, event_timeout=event_timeout)


def make_block_view(controller, context, data):
    class BlockSubclass(Block):
        def __init__(self):
            self._do_init(controller, context, data)

    for endpoint in data:
        # make properties for the endpoints we know about
        make_get_property(BlockSubclass, endpoint)

    block = BlockSubclass()
    return block