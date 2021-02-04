import re
from typing import (
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from annotypes import Anno

from malcolm.compat import OrderedDict

from .camel import CAMEL_RE
from .context import Context
from .hook import Hook, Hookable
from .info import Info
from .models import AttributeModel, MethodMeta, MethodModel
from .request import Request

T = TypeVar("T")


Field = Union[AttributeModel, MethodModel]
FieldDict = Dict[object, List[Tuple[str, Field, Callable, bool]]]
Info_co = TypeVar("Info_co", covariant=True, bound=Info)
object_co = TypeVar("object_co", covariant=True)
Callback = Callable[[object_co, Info_co], None]
Hooked = Callable[..., T]
ArgsGen = Callable[[List[str]], List[str]]

with Anno("The name of the Part within the Controller"):
    APartName = str

# Part names are alphanumeric with underscores and dashes. Dots not allowed as
# web gui uses dot as "something that can't appear in field or part names"
PART_NAME_RE = re.compile(r"[a-zA-Z_\-0-9]*$")


class FieldRegistry:
    def __init__(self) -> None:
        self.fields: FieldDict = OrderedDict()

    def get_field(self, name: str) -> Field:
        for fields in self.fields.values():
            for (n, field, _, _) in fields:
                if n == name:
                    return field
        raise ValueError("No field named %s found" % (name,))

    def add_method_model(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        owner: object = None,
        needs_context: bool = False,
    ) -> MethodModel:
        """Register a function to be added to the block"""
        if name is None:
            name = func.__name__
        without: Union[Tuple[str], Tuple[()]]
        if needs_context:
            call_types = getattr(func, "call_types", {})
            context_anno: Anno = call_types.get("context", None)
            assert context_anno, (
                "Func %s needs_context, but has no 'context' anno. Did "
                "you forget the @add_call_types decorator?" % func
            )
            assert list(call_types)[0] == "context", (
                "Func %s needs_context, so 'context' needs to be the first "
                "argument it takes" % func
            )
            assert context_anno.typ is Context, (
                "Func %s needs_context, but 'context' has type %s rather than"
                "Context" % (func, context_anno.typ)
            )
            without = ("context",)
        else:
            without = ()
        method = MethodModel(
            meta=MethodMeta.from_callable(func, description, without_takes=without)
        )
        self._add_field(owner, name, method, func, needs_context)
        return method

    def add_attribute_model(
        self,
        name: str,
        attr: AttributeModel,
        writeable_func: Optional["Callable"] = None,
        owner: object = None,
        needs_context: bool = False,
    ) -> AttributeModel:
        self._add_field(owner, name, attr, writeable_func, needs_context)
        return attr

    def _add_field(
        self,
        owner: object,
        name: str,
        model: Field,
        writeable_func: Optional["Callable"] = None,
        needs_context: bool = False,
    ) -> None:
        assert CAMEL_RE.match(name), "Field %r published by %s is not camelCase" % (
            name,
            owner,
        )
        for o, fields in self.fields.items():
            existing = [x for x in fields if x[0] == name]
            assert (
                not existing
            ), "Field %r published by %s would overwrite one made by %s" % (
                name,
                owner,
                o,
            )
        part_fields = self.fields.setdefault(owner, [])
        part_fields.append((name, model, cast(Callable, writeable_func), needs_context))


class InfoRegistry:
    def __init__(self):
        self._reportable_infos: Dict[Type[Info], Callback] = {}

    def add_reportable(self, info: Type[Info], callback: Callback) -> None:
        self._reportable_infos[info] = callback

    def report(self, reporter: object, info: Info) -> None:
        typ = type(info)
        try:
            callback = self._reportable_infos[typ]
        except KeyError:
            raise ValueError(
                "Don't know how to report a %s, only %s\n"
                "Did you use the wrong type of Controller?"
                % (typ.__name__, [x.__name__ for x in self._reportable_infos])
            )
        callback(reporter, info)


class Part(Hookable):
    registrar: Optional["PartRegistrar"] = None

    def __init__(self, name: APartName) -> None:
        assert PART_NAME_RE.match(name), (
            "Expected Alphanumeric part name (dashes and underscores allowed)"
            + " got %r" % name
        )
        self.set_logger(part_name=name)
        self.name: str = name

    def setup(self, registrar: "PartRegistrar") -> None:
        """Use the given `PartRegistrar` to populate the hooks and fields.
        This function is called for all parts in a block when the block's
        `Controller` is added to a `Process`"""
        self.registrar = registrar

    def notify_dispatch_request(self, request: Request) -> None:
        """Will be called when a context passed to a hooked function is about
        to dispatch a request"""
        pass


class PartRegistrar:
    """Utility object that allows Parts to register Methods and Attributes
    with their parent Controller that will appear in the Block
    """

    def __init__(
        self, field_registry: FieldRegistry, info_registry: InfoRegistry, part: "Part"
    ) -> None:
        self._field_registry = field_registry
        self._info_registry = info_registry
        self._part = part

    def hook(
        self,
        hooks: Union[Type[Hook], Sequence[Type[Hook]]],
        func: Hooked,
        args_gen: Optional[ArgsGen] = None,
    ):
        """Register func to be run when any of the hooks are run by parent

        Args:
            hooks: A Hook class or list of Hook classes of interest
            func: The callable that should be run on that Hook
            args_gen: Optionally specify the argument names that should be
                passed to func. If not given then use func.call_types.keys
        """
        # TODO: move the hook functionality here out of the part
        self._part.register_hooked(hooks, func, args_gen)

    def add_method_model(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        needs_context: bool = False,
    ) -> MethodModel:
        """Register a function to be added to the Block as a MethodModel

        Args:
            func: The callable that will be called when the Method is called
            name: Override name, if None then take function __name__
            description: Override description, if None take function.__doc__
            needs_context: If True the "context" argument will be supplied to
                func with a newly created `Context` instance
        """
        return self._field_registry.add_method_model(
            func, name, description, self._part, needs_context
        )

    def add_attribute_model(
        self,
        name: str,
        attr: AttributeModel,
        writeable_func: Optional["Callable"] = None,
        needs_context: bool = False,
    ) -> AttributeModel:
        """Register a pre-existing AttributeModel to be added to the Block"""
        return self._field_registry.add_attribute_model(
            name, attr, writeable_func, self._part, needs_context
        )

    def report(self, info: Info) -> None:
        """Report an Info to the parent Controller"""
        self._info_registry.report(self._part, info)
