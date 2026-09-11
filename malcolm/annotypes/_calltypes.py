import inspect
import re
import tokenize
from collections import OrderedDict

from ._anno import Anno, NO_DEFAULT, make_repr, anno_with_default
from ._compat import add_metaclass, getargspec, func_globals
from ._typing import TYPE_CHECKING, GenericMeta, Any

if TYPE_CHECKING:  # pragma: no cover
    from typing import Dict, Callable, Tuple, List

type_re = re.compile('^# type: ([^-]*)( -> (.*))?$')


class CallTypesMeta(GenericMeta):
    def __init__(cls, name, bases, dct, **kwargs):
        f = dct.get('__init__', None)
        if f:
            cls.call_types, _ = make_call_types(f, func_globals(f))
        elif getattr(cls, "call_types", None) is not None:
            cls.call_types = OrderedDict(cls.call_types)
        else:
            cls.call_types = OrderedDict()
        cls.return_type = Anno("Class instance", name="Instance").set_typ(cls)
        super(CallTypesMeta, cls).__init__(name, bases, dct, **kwargs)

    def matches_type(self, cls):
        if not inspect.isclass(cls):
            return False
        else:
            return issubclass(cls, self)


@add_metaclass(CallTypesMeta)
class WithCallTypes(object):
    call_types = None  # type: Dict[str, Anno]
    return_type = None  # type: Anno

    def __repr__(self):
        repr_str = make_repr(self, self.call_types)
        return repr_str


def add_call_types(f):
    f.call_types, f.return_type = make_call_types(f, func_globals(f))
    return f


def make_call_types(f, globals_d):
    # type: (Callable, Dict) -> Tuple[Dict[str, Anno], Anno]
    """Make a call_types dictionary that describes what arguments to pass to f

    Args:
        f: The function to inspect for argument names (without self)
        globals_d: A dictionary of globals to lookup annotation definitions in
    """
    arg_spec = getargspec(f)
    args = [k for k in arg_spec.args if k != "self"]

    defaults = {}  # type: Dict[str, Any]
    if arg_spec.defaults:
        default_args = args[-len(arg_spec.defaults):]
        for a, default in zip(default_args, arg_spec.defaults):
            defaults[a] = default

    if not getattr(f, "__annotations__", None):
        # Make string annotations from the type comment if there is one
        annotations = make_annotations(f, globals_d)
    else:
        annotations = f.__annotations__

    call_types = OrderedDict()  # type: Dict[str, Anno]
    for a in args:
        anno = anno_with_default(annotations[a], defaults.get(a, NO_DEFAULT))
        assert isinstance(anno, Anno), \
            "Argument %r has type %r which is not an Anno" % (a, anno)
        call_types[a] = anno

    return_type = anno_with_default(annotations.get("return", None))
    if return_type is Any:
        return_type = Anno("Any return value", name="return").set_typ(Any)
    assert return_type is None or isinstance(return_type, Anno), \
        "Return has type %r which is not an Anno" % (return_type,)

    return call_types, return_type


class EchoStr(str):
    def __getitem__(self, item):
        if isinstance(item, tuple):
            # obj["x", "y"] is obj.__getitem__(("x", "y"))
            str_items = []
            for x in item:
                if x is Ellipsis:
                    str_items.append("...")
                else:
                    str_items.append(str(x))
            item = ", ".join(str_items)
        return "%s[%s]" % (self, item)

    def __getattr__(self, item):
        return "%s.%s" % (self, item)


class EchoDict(dict):
    # A fake globals dictionary that just returns the string back
    def __getitem__(self, item):
        return EchoStr(item)


def make_annotations(f, globals_d=None):
    # type: (Callable, Dict) -> Dict[str, Any]
    """Create an annotations dictionary from Python2 type comments

    http://mypy.readthedocs.io/en/latest/python2.html

    Args:
        f: The function to examine for type comments
        globals_d: The globals dictionary to get type idents from. If not
            specified then make the annotations dict contain strings rather
            than the looked up objects
    """
    locals_d = {}  # type: Dict[str, Any]
    if globals_d is None:
        # If not given a globals_d then we should just populate annotations with
        # the strings in the type comment.
        globals_d = {}
        # The current approach is to use eval, which means manufacturing a
        # dict like object that will just echo the string back to you. This
        # has a number of complexities for somthing like numpy.number or
        # Callable[..., int], which are handled in EchoStr above, so it might be
        # better off as an ast.parse in the future...
        locals_d = EchoDict()
    lines, _ = inspect.getsourcelines(f)
    arg_spec = getargspec(f)
    args = list(arg_spec.args)
    if arg_spec.varargs is not None:
        args.append(arg_spec.varargs)
    if arg_spec.keywords is not None:
        args.append(arg_spec.keywords)
    it = iter(lines)
    types = []  # type: List
    found = None
    for token in tokenize.generate_tokens(lambda: next(it)):
        typ, string, start, end, line = token
        if typ == tokenize.COMMENT:
            found = type_re.match(string)
            if found:
                parts = found.groups()
                # (...) is used to represent all the args so far
                if parts[0] != "(...)":
                    expr = parts[0].replace("*", "")
                    try:
                        ob = eval(expr, globals_d, locals_d)
                    except Exception as e:
                        raise ValueError(
                            "Error evaluating %r: %s" % (expr, e))
                    if isinstance(ob, tuple):
                        # We got more than one argument
                        types += list(ob)
                    else:
                        # We got a single argument
                        types.append(ob)
                if parts[1]:
                    # Got a return, done
                    try:
                        ob = eval(parts[2], globals_d, locals_d)
                    except Exception as e:
                        raise ValueError(
                            "Error evaluating %r: %s" % (parts[2], e))
                    if args and args[0] in ["self", "cls"]:
                        # Allow the first argument to be inferred
                        if len(args) == len(types) + 1:
                            args = args[1:]
                    assert len(args) == len(types), \
                        "Args %r Types %r length mismatch" % (args, types)
                    ret = dict(zip(args, types))
                    ret["return"] = ob
                    return ret
    if found:
        # If we have ever found a type comment, but not the return value, error
        raise ValueError("Got to the end of the function without seeing ->")
    return {}
