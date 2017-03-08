class View(object):
    """View of a Model to allow Put, Get, Subscribe etc."""
    _lock_set_attr = False
    _controller = None
    _context = None
    _data = None

    def __init__(self):
        raise NotImplementedError("View must be instantiated with make_view()")

    def __setattr__(self, name, value):
        if self._lock_set_attr:
            raise NameError("Cannot set attribute %s on view" % name)
        else:
            object.__setattr__(self, name, value)

    def _prepare_endpoints(self, data):
        for endpoint in data:
            # Add _subscribe methods for each endpoint
            self._make_subscribe_method(endpoint)

    def _make_subscribe_method(self, endpoint):
        # Make subscribe_endpoint method
        def subscribe_child(callback, *args, **kwargs):
            return self._context.subscribe(
                self._data.path + [endpoint], callback, *args, **kwargs)

        setattr(self, "subscribe_%s" % endpoint, subscribe_child)


def make_view(controller, context, data, cls=View):
    # Properties can only be set on classes, so make subclass that we can use

    class ViewSubclass(cls):
        def __init__(self):
            self._controller = controller
            self._context = context
            self._data = data
            self._prepare_endpoints(data)
            self._lock_set_attr = True

    for endpoint in data:
        # make properties for the endpoints we know about
        make_get_property(ViewSubclass, endpoint)

    view = ViewSubclass()
    return view


def make_get_property(cls, endpoint):
    @property
    def make_child_view(self):
        # Get the child of self._data. Needs to be done by the controller to
        # make sure lock is taken and we get consistent data
        child = self._controller.make_view(self._data, self._context, endpoint)
        return child

    setattr(cls, endpoint, make_child_view)


