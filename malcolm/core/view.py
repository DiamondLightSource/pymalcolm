class View(object):
    """View of a Model to allow Put, Get, Subscribe etc."""
    _lock_set_attr = False
    _controller = None
    _context = None
    _data = None
    _endpoints = ()

    def __init__(self):
        raise NotImplementedError("View must be instantiated with make_view()")

    def _do_init(self, controller, context, data):
        # This will be called by the subclass created in make_view
        self._controller = controller
        self._context = context
        self._data = data
        self._prepare_endpoints(data)
        self._lock_set_attr = True

    def _prepare_endpoints(self, data):
        self._endpoints = tuple(data)
        for endpoint in self._endpoints:
            # Add _subscribe methods for each endpoint
            self._make_subscribe_method(endpoint)

    def __iter__(self):
        return iter(self._endpoints)

    def to_dict(self):
        return self._data.to_dict()

    def __getitem__(self, item):
        try:
            return getattr(self, item)
        except AttributeError:
            return KeyError(item)

    def __setattr__(self, name, value):
        if self._lock_set_attr:
            raise NameError("Cannot set attribute %s on view" % name)
        else:
            object.__setattr__(self, name, value)

    def _make_subscribe_method(self, endpoint):
        # Make subscribe_endpoint method
        def subscribe_child(callback, *args, **kwargs):
            return self._context.subscribe(
                self._data.path + [endpoint], callback, *args, **kwargs)

        setattr(self, "subscribe_%s" % endpoint, subscribe_child)


def make_get_property(cls, endpoint):
    @property
    def make_child_view(self):
        # Get the child of self._data. Needs to be done by the controller to
        # make sure lock is taken and we get consistent data
        child = self._controller.make_view(self._context, self._data, endpoint)
        return child

    setattr(cls, endpoint, make_child_view)


def make_view(controller, context, data, cls=View):
    """Make a View subclass containing properties specific for given data

    Args:
        controller (Controller): The child _controller that hosts the data
        context (Context): The context the parent has made that the View should
            use for manipulating the data
        data (Model): The actual data that context will be manipulating
        cls (View): The baseclass of the created View. Specify this if you
            need custom functions/properties in your created View instance

    Returns:
        View: A View subclass instance that provides a user-focused API to
            the given data
    """
    # Properties can only be set on classes, so make subclass that we can use

    class ViewSubclass(cls):
        def __init__(self):
            self._do_init(controller, context, data)

    for endpoint in data:
        # make properties for the endpoints we know about
        make_get_property(ViewSubclass, endpoint)

    view = ViewSubclass()
    return view





