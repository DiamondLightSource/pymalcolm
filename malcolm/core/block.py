from .methodmodel import MethodModel
from .view import View


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

        setattr(self, "%s_async" % endpoint, post_async)

    def put_attribute_values_async(self, params):
        futures = []
        for attr, value in params.items():
            assert hasattr(self, attr), \
                "Block does not have attribute %s" % attr
            future = self._context.put_async(
                self._data.path + [attr, "value"], value)
            futures.append(future)
        return futures

    def put_attribute_values(self, params, timeout=None):
        futures = self.put_attribute_values_async(params)
        self._context.wait_all_futures(futures, timeout=timeout)

    def when_value_matches(self, attr, good_value, bad_values=None,
                           timeout=None):
        future = self.when_value_matches_async(attr, good_value, bad_values)
        self._context.wait_all_futures(future, timeout)

    def when_value_matches_async(self, attr, good_value, bad_values=None):
        path = self._data.path + [attr, "value"]
        future = self._context.when_matches_async(path, good_value, bad_values)
        return future
