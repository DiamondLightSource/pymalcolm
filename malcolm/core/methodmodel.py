import inspect

from malcolm.compat import str_, OrderedDict
from .map import Map
from .mapmeta import MapMeta
from .meta import Meta
from .serializable import Serializable, deserialize_object, check_camel_case, \
    serialize_object

REQUIRED = object()
OPTIONAL = object()


@Serializable.register_subclass("malcolm:core/Method:1.0")
class MethodModel(Meta):
    """Exposes a function with metadata for arguments and return values"""

    endpoints = ["takes", "defaults", "description", "tags", "writeable",
                 "label", "returns"]

    def __init__(self, description="", tags=(), writeable=True, label="",
                 takes=None, defaults=None, returns=None):
        super(MethodModel, self).__init__(description, tags, writeable, label)
        self.takes = self.set_takes(takes)
        self.returns = self.set_returns(returns)
        self.defaults = self.set_defaults(defaults)

    def set_notifier_path(self, notifier, path):
        super(MethodModel, self).set_notifier_path(notifier, path)
        for endpoint in ["takes", "returns"]:
            self[endpoint].set_notifier_path(notifier, self.path + [endpoint])

    def set_takes(self, takes):
        """Set the takes MapMeta"""
        if takes is None:
            takes = MapMeta()
        else:
            takes = deserialize_object(takes, MapMeta)
        if hasattr(self, "takes"):
            self.takes.set_notifier_path(None, ())
        takes.set_notifier_path(self.notifier, self.path + ["takes"])
        return self.set_endpoint_data("takes", takes)

    def set_defaults(self, defaults):
        """Set the defaults dict"""
        if defaults is None:
            defaults = {}
        for k, v in defaults.items():
            if k != "typeid":
                k = deserialize_object(k, str_)
                defaults[k] = self.takes.elements[k].validate(v)
        return self.set_endpoint_data("defaults", defaults)

    def set_returns(self, returns):
        """Set the returns MapMeta"""
        if returns is None:
            returns = MapMeta()
        else:
            returns = deserialize_object(returns, MapMeta)
        if hasattr(self, "returns"):
            self.returns.set_notifier_path(None, ())
        returns.set_notifier_path(self.notifier, self.path + ["returns"])
        return self.set_endpoint_data("returns", returns)

    def prepare_call_args(self, **param_dict):
        args = []
        # Prepare input map
        if self.takes.elements:
            params = Map(self.takes, self.defaults)
            params.update(param_dict)
            params.check_valid()
            args.append(params)
        # Prepare output map
        if self.returns.elements:
            ret = Map(self.returns)
            args.append(ret)
        return tuple(args)

    @classmethod
    def wrap_method(cls, func):
        """Checks if a function already has a MethodModel implementation of 
        itself and if it does not, creates one.

        Args:
            func: Function to wrap

        Returns:
            callable: Function with MethodModel instance of itself as an
                attribute
        """

        if not hasattr(func, "MethodModel"):
            # Make a new one
            description = inspect.getdoc(func) or ""
            method = cls(description)
        else:
            # Copy it in case we are subclassing
            method = cls.from_dict(func.MethodModel.to_dict())
            method.set_writeable_in(*func.MethodModel.writeable_in)

        func.MethodModel = method
        return func

    def recreate_from_others(self, method_metas, without=()):
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
        takes.set_elements(elements)
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

    # Setup the takes MapMeta and attach it to the function's MethodModel
    meta = MapMeta()
    meta.set_elements(elements)
    meta.set_required(required)
    return meta, defaults


def method_takes(*args):
    """Checks if function has a MethodModel representation, calls wrap_method to
    create one if it doesn't and then adds the takes attribute to it
    from \*args

    Args:
        \*args(list): List of of length nparams*3. List of form:
            [name, `VMeta`, `REQUIRED`/`OPTIONAL`/default, ...]

    Returns:
        callable: Updated function
    """

    def decorator(func):
        MethodModel.wrap_method(func)
        takes_meta, defaults = _prepare_map_meta(args, allow_defaults=True)
        func.MethodModel.set_takes(takes_meta)
        func.MethodModel.set_defaults(defaults)
        return func

    return decorator


def method_also_takes(*args):
    """As `method_takes`, but adds \*args to method takes instead of replacing
    """

    def decorator(func):
        assert inspect.isclass(func), \
            "method_also_takes() only works on a Class, not %r" % func
        MethodModel.wrap_method(func)
        takes_meta, defaults = _prepare_map_meta(
            args, allow_defaults=True,
            elements=serialize_object(func.MethodModel.takes.elements),
            defaults=func.MethodModel.defaults.copy(),
            required=list(func.MethodModel.takes.required)
        )
        func.MethodModel.set_takes(takes_meta)
        func.MethodModel.set_defaults(defaults)
        return func

    return decorator


def method_returns(*args):
    """Checks if function has a MethodModel representation, calls wrap_method to
    create one if it doesn't and then adds the returns attribute to it
    from \*args

    Args:
        \*args(list): List of of length nparams*3. List of form:
            [name, `VMeta`, `REQUIRED`/`OPTIONAL`/default, ...]

    Returns:
        callable: Updated function
    """

    def decorator(func):
        MethodModel.wrap_method(func)
        returns_meta, _ = _prepare_map_meta(args, allow_defaults=False)
        func.MethodModel.set_returns(returns_meta)
        return func

    return decorator


def method_writeable_in(*states):
    """Checks if function has a MethodModel representation, calls wrap_method to
    create one if it doesn't and then adds only_in to it from \*states

    Args:
        \*states(list): List of state names, like DefaultStateMachine.RESETTING

    Returns:
        callable: Updated function
    """
    def decorator(func):
        MethodModel.wrap_method(func)
        func.MethodModel.set_writeable_in(*states)
        return func
    return decorator


def get_method_decorated(instance):
    for name, member in inspect.getmembers(instance, inspect.ismethod):
        if hasattr(member, "MethodModel"):
            # Copy it so we get a new one for this instance
            method_model = MethodModel.from_dict(member.MethodModel.to_dict())
            method_model.writeable_in = member.MethodModel.writeable_in
            yield name, method_model, member


def create_class_params(cls, **kwargs):
    method_model = cls.MethodModel
    params = method_model.prepare_call_args(**kwargs)[0]
    return params


def call_with_params(func, *args, **params):
    method_model = func.MethodModel
    args += method_model.prepare_call_args(**params)
    return func(*args)
