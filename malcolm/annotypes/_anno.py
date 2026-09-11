import copy
import sys

from ._typing import TYPE_CHECKING, Union, MappingOrigin
from ._array import Array, to_array

if TYPE_CHECKING:  # pragma: no cover
    from typing import Dict, Set, Optional, Any, Sequence, Union, Type

# Signifies that this is a return value and the default value should be inferred
RETURN_DEFAULT = object()

# Signifies that no default value has been set
NO_DEFAULT = object()


def anno_with_default(src, default=RETURN_DEFAULT):
    # type: (Any, Any) -> Anno
    origin = getattr(src, "__origin__", None)
    if origin == Union:
        # if any of the types are NoneType then it is optional
        optional = type(None) in src.__args__
        # the anno is actually the first parameter to Optional or Union
        anno = src.__args__[0]  # type: Anno
        assert isinstance(anno, Anno), \
            "Expected Optional[Anno], Union[Anno,...] or Anno, got %r" % (anno,)
        # if this is a return type and optional, default should be None
        if optional:
            if default is RETURN_DEFAULT:
                default = None
            assert default is None, \
                "Expected Optional[Anno] with default=None, got %r with " \
                "default=%r" % (anno, default)
    else:
        anno = src
    # Make a copy of the anno with the new default if needed
    if default not in (RETURN_DEFAULT, NO_DEFAULT):
        anno = copy.copy(anno)
        anno.default = default
    return anno


def caller_locals():
    # type: () -> Dict
    """Return the frame object for the caller's stack frame."""
    try:
        raise ValueError
    except ValueError:
        _, _, tb = sys.exc_info()
        assert tb, "Can't get traceback, this shouldn't happen"
        caller_frame = tb.tb_frame.f_back.f_back
        return caller_frame.f_locals


def make_repr(inst, attrs):
    # type: (object, Sequence[str]) -> str
    """Create a repr from an instance of a class

    Args:
        inst: The class instance we are generating a repr of
        attrs: The attributes that should appear in the repr
    """
    arg_str = ", ".join(
        "%s=%r" % (a, getattr(inst, a)) for a in attrs if hasattr(inst, a))
    repr_str = "%s(%s)" % (inst.__class__.__name__, arg_str)
    return repr_str


class Anno(object):
    def __init__(self, description, name=None, default=NO_DEFAULT):
        # type: (str, str, Any) -> None
        """Annotate a type with run-time accessible metadata

        Args:
            description: A one-line description for the argument
            name: The name of the Anno, can also be set via context manager
        """
        self.description = description  # type: str
        self.name = name  # type: Optional[str]
        self.default = default  # type: Any
        self.typ = None  # type: Any
        self.is_array = False  # type: Optional[bool]
        self.is_mapping = False  # type: Optional[bool]
        self._names_on_enter = None  # type: Optional[Set[str]]
        self._array_cls = None  # type: Optional[Type[Array]]
        # TODO: add min, max, maybe widget

    def __call__(self, *args, **kwargs):
        """Pass calls through to our underlying type"""
        if self.is_array:
            return to_array(Array[self.typ], *args, **kwargs)
        elif self.is_mapping:
            raise TypeError("Type Mapping cannot be instantiated")
        else:
            return self.typ(*args, **kwargs)

    def __repr__(self):
        attrs = ["name", "typ", "description"]
        return make_repr(self, attrs)

    def __enter__(self):
        """Use as a context manager to set typ and name without stamping on
        the definitions for static analysis. For example:

        >>> with Anno("The arg to take"):
        ...     MyArg = str

        is equivalent to:

        >>> MyArg = str
        >>> if not TYPE_CHECKING:
        ...     MyArg = Anno("The arg to take", name="MyArg").set_typ(str)
        """
        self._names_on_enter = set(caller_locals())

    def _get_defined_name(self, locals_d):
        defined = set(locals_d) - self._names_on_enter
        assert len(defined) == 1, \
            "Expected a single type to be defined, got %s" % list(defined)
        self.name = defined.pop()

    def set_typ(self, typ, is_array=False, is_mapping=False):
        self.typ = typ
        assert is_array is False or is_mapping is False, \
            "Can't have both and array and mapping"
        self.is_array = is_array
        if is_array:
            self._array_cls = Array[typ]
        self.is_mapping = is_mapping
        return self

    def _get_type(self, typ):
        origin = getattr(typ, "__origin__", None)
        if origin == Array:
            # This is an array
            self.set_typ(typ.__args__[0], is_array=True)
        elif origin == MappingOrigin:
            # This is a dict
            assert len(typ.__args__) == 2, \
                "Expected Mapping[ktyp, vtyp], got %r" % typ
            self.set_typ(typ.__args__, is_mapping=True)
        elif origin is None:
            # This is a bare type
            self.set_typ(typ)
        else:
            raise ValueError("Cannot annotate a type with origin %r" % origin)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            return False
        locals_d = caller_locals()
        self._get_defined_name(locals_d)
        self._get_type(locals_d[self.name])
        locals_d[self.name] = self

