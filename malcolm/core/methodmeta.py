import inspect

from malcolm.compat import str_, OrderedDict
from malcolm.core.elementmap import ElementMap
from malcolm.core.map import Map
from malcolm.core.mapmeta import MapMeta
from malcolm.core.meta import Meta
from malcolm.core.request import Post
from malcolm.core.serializable import Serializable, deserialize_object, \
    check_camel_case

REQUIRED = object()
OPTIONAL = object()


@Serializable.register_subclass("malcolm:core/MethodMeta:1.0")
class MethodMeta(Meta):
    """Exposes a function with metadata for arguments and return values"""

    endpoints = ["takes", "defaults", "description", "tags", "writeable",
                 "label", "returns"]

    def __init__(self, description="", tags=None, writeable=True, label=""):
        super(MethodMeta, self).__init__(description, tags, writeable, label)
        self.set_takes(MapMeta())
        self.set_returns(MapMeta())
        self.set_defaults(OrderedDict())

    def set_takes(self, takes, notify=True):
        """Set the arguments and default values for the method

        Args:
            takes (MapMeta): Arguments to the function
        """
        takes = deserialize_object(takes, MapMeta)
        self.set_endpoint_data("takes", takes, notify)

    def set_defaults(self, defaults, notify=True):
        """Set the default dict"""
        for k, v in defaults.items():
            assert isinstance(k, str_), \
                "Expected string, got %s" % (k,)
            defaults[k] = self.takes.elements[k].validate(v)
        self.set_endpoint_data("defaults", defaults, notify)

    def set_returns(self, returns, notify=True):
        """Set the return parameters for the method to validate against"""
        returns = deserialize_object(returns, MapMeta)
        self.set_endpoint_data("returns", returns, notify)

    def handle_request(self, request, post_function):
        self.log_debug("Received request %s", request)
        assert isinstance(request, Post), "Expected Post, got %r" % (request,)
        assert len(request.endpoint) == 2, "Can only Post to MethodMeta root"
        return self.call_post_function(post_function, request.parameters, self)

    def prepare_input_map(self, **param_dict):
        params = Map(self.takes, self.defaults)
        if param_dict:
            params.update(param_dict)
        params.check_valid()
        return params

    def call_post_function(self, post_function, param_dict, *args):
        need_params = bool(self.takes.elements)
        need_ret = bool(self.returns.elements)
        args = list(args)
        # Prepare input map
        if need_params:
            if param_dict is None:
                param_dict = {}
            params = self.prepare_input_map(**param_dict)
            args.append(params)

        # Prepare output map
        if need_ret:
            ret = Map(self.returns)
            args.append(ret)

        self.log_debug("Calling with %s" % (args,))

        result = post_function(*args)
        if need_ret:
            result = Map(self.returns, result)
            result.check_valid()

        return result

    @classmethod
    def wrap_method(cls, func):
        """
        Checks if a function already has a MethodMeta implementation of itself and
        if it does not, creates one.

        Args:
            func: Function to wrap

        Returns:
            callable: Function with MethodMeta instance of itself as an attribute
        """

        if not hasattr(func, "MethodMeta"):
            # Make a new one
            description = inspect.getdoc(func) or ""
            method = cls(description)
        else:
            # Copy it in case we are subclassing
            method = MethodMeta.from_dict(func.MethodMeta.to_dict())
            method.writeable_in = func.MethodMeta.writeable_in

        func.MethodMeta = method
        return func

    def recreate_from_others(self, method_metas, without=None):
        if without is None:
            without = []
        defaults = OrderedDict()
        elements = OrderedDict()
        required = []

        # Populate the intermediate data structures
        for method_meta in method_metas:
            for element in method_meta.takes.elements:
                if element not in without:
                    # Serialize it to copy it
                    serialized = method_meta.takes.elements[element].to_dict()
                    elements[element] = serialized
                    if element in method_meta.takes.required and \
                                    element not in required:
                        required.append(element)
                    if element in method_meta.defaults:
                        defaults.pop(element, None)
                        defaults[element] = method_meta.defaults[element]
                    # TODO: what about returns?

        # remove required args that are now defaulted
        required = [r for r in required if r not in defaults]

        # Update ourself from these structures
        takes = MapMeta()
        takes.set_elements(ElementMap(elements))
        takes.set_required(required)
        self.set_takes(takes)
        self.set_defaults(defaults)


def _prepare_map_meta(args, allow_defaults, defaults=None, elements=None,
                      required=None):
    # prepare some data structures that will be used for the takes MapMeta
    if defaults is None:
        defaults = OrderedDict()
    if elements is None:
        elements = OrderedDict()
    if required is None:
        required = []
    for index in range(0, len(args), 3):
        # pick out 3 arguments
        name = args[index]
        check_camel_case(name)
        meta = args[index + 1]
        default = args[index + 2]
        # store them in the right structures
        elements[name] = meta
        if default is REQUIRED:
            required.append(name)
        elif default is not OPTIONAL:
            assert allow_defaults, \
                "Defaults not allowed in this structure"
            defaults[name] = default

    # Setup the takes MapMeta and attach it to the function's MethodMeta
    meta = MapMeta()
    meta.set_elements(ElementMap(elements))
    meta.set_required(required)
    return meta, defaults


def method_takes(*args):
    """Checks if function has a MethodMeta representation, calls wrap_method to
    create one if it doesn't and then adds the takes attribute to it
    from \*args

    Args:
        \*args(list): List of of length nparams*3. List of form:
            [name, `VMeta`, `REQUIRED`/`OPTIONAL`/default, ...]

    Returns:
        callable: Updated function
    """

    def decorator(func):
        MethodMeta.wrap_method(func)
        takes_meta, defaults = _prepare_map_meta(args, allow_defaults=True)
        func.MethodMeta.set_takes(takes_meta)
        func.MethodMeta.set_defaults(defaults)
        return func

    return decorator


def method_also_takes(*args):
    """As `method_takes`, but adds \*args to method takes instead of replacing
    """

    def decorator(func):
        MethodMeta.wrap_method(func)
        takes_meta, defaults = _prepare_map_meta(
            args, allow_defaults=True,
            elements=func.MethodMeta.takes.elements.to_dict(),
            defaults=func.MethodMeta.defaults.copy(),
            required=list(func.MethodMeta.takes.required)
        )
        func.MethodMeta.set_takes(takes_meta)
        func.MethodMeta.set_defaults(defaults)
        return func

    return decorator


def method_returns(*args):
    """Checks if function has a MethodMeta representation, calls wrap_method to
    create one if it doesn't and then adds the returns attribute to it
    from \*args

    Args:
        \*args(list): List of of length nparams*3. List of form:
            [name, `VMeta`, `REQUIRED`/`OPTIONAL`/default, ...]

    Returns:
        callable: Updated function
    """

    def decorator(func):
        MethodMeta.wrap_method(func)
        returns_meta, _ = _prepare_map_meta(args, allow_defaults=False)
        func.MethodMeta.set_returns(returns_meta)
        return func

    return decorator


def method_writeable_in(*states):
    """Checks if function has a MethodMeta representation, calls wrap_method to
    create one if it doesn't and then adds only_in to it from \*states

    Args:
        \*states(list): List of state names, like DefaultStateMachine.RESETTING

    Returns:
        callable: Updated function
    """
    def decorator(func):
        MethodMeta.wrap_method(func)
        func.MethodMeta.set_writeable_in(*states)
        return func
    return decorator


def get_method_decorated(instance):
    for name, member in inspect.getmembers(instance, inspect.ismethod):
        if hasattr(member, "MethodMeta"):
            # Copy it so we get a new one for this instance
            method = MethodMeta.from_dict(member.MethodMeta.to_dict())
            method.set_logger_name("%s.%s.MethodMeta" % (
                instance.__class__.__name__, name))
            method.writeable_in = member.MethodMeta.writeable_in
            yield name, method, member
