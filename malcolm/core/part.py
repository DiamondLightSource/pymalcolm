from annotypes import Anno, TYPE_CHECKING, WithCallTypes

from malcolm.compat import OrderedDict
from .hook import Hookable
from .info import Info
from .models import MethodModel, VMeta, MapMeta, AttributeModel

with Anno("The name of the Part within the Controller"):
    APartName = str

if TYPE_CHECKING:
    from typing import Callable, Optional


if TYPE_CHECKING:
    from typing import Union, List, Tuple, Dict, Callable, Optional, Type
    Field = Union[AttributeModel, MethodModel]
    FieldDict = Dict[object, List[Tuple[str, Field, Callable]]]
    Callback = Callable[[object, Info], None]


class FieldRegistry(object):
    def __init__(self):
        # type: () -> None
        self.fields = OrderedDict()  # type: FieldDict

    def add_method_model(self,
                         func,  # type: Callable
                         name=None,  # type: Optional[str]
                         description=None,  # type: Optional[str]
                         owner=None,  # type: object
                         ):
        # type: (...) -> MethodModel
        """Register a function to be added to the block"""
        if name is None:
            name = func.__name__
        if description is None:
            description = func.__doc__
        method = MethodModel(description=description)
        takes_elements = OrderedDict()
        for k, anno in getattr(func, "call_types", {}).items():
            cls = VMeta.lookup_annotype_converter(anno)
            takes_elements[k] = cls.from_annotype(anno, writeable=True)
        method.set_takes(MapMeta(elements=takes_elements))
        returns_elements = OrderedDict()
        return_type = getattr(func, "return_type", None)  # type: Anno
        if return_type:
            assert isinstance(return_type.typ, WithCallTypes), \
                "Expected return typ WithCallTypes, got %s" % (return_type.typ,)
            for k, anno in return_type.typ.call_types.items():
                cls = VMeta.lookup_annotype_converter(return_type)
                returns_elements[k] = cls.from_annotype(anno, writeable=False)
        method.set_returns(MapMeta(elements=returns_elements))
        self._add_field(owner, name, method, func)
        return method

    def add_attribute_model(self,
                            name,  # type: str
                            attr,  # type: AttributeModel
                            writeable_func=None,  # type: Optional[Callable]
                            owner=None,  # type: object
                            ):
        # type: (...) -> AttributeModel
        self._add_field(owner, name, attr, writeable_func)
        return attr

    def _add_field(self, owner, name, model, writeable_func):
        # type: (object, str, Field, Callable) -> None
        part_fields = self.fields.setdefault(owner, [])
        part_fields.append((name, model, writeable_func))


class InfoRegistry(object):
    def __init__(self):
        # type: () -> None
        self.reportable_infos = {}  # type: Dict[Type[Info], Callback]

    def add_reportable(self, info, callback):
        # type: (Type[Info], Callback) -> None
        self.reportable_infos[info] = callback


class Part(Hookable):
    def __init__(self, name):
        # type: (APartName) -> None
        super(Part, self).__init__(name=name)
        self.name = name

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        """Use the given Registrar to populate the hooks and fields"""
        raise NotImplementedError()


class PartRegistrar(object):
    def __init__(self, field_registry, info_registry, part):
        # type: (FieldRegistry, InfoRegistry, Part) -> None
        self._field_registry = field_registry
        self._info_registry = info_registry
        self._part = part

    def add_method_model(self,
                         func,  # type: Callable
                         name=None,  # type: Optional[str]
                         description=None,  # type: Optional[str]
                         ):
        # type: (...) -> MethodModel
        """Register a function to be added to the block"""
        return self._registry.add_method_model(
            self._part, func, name, description)

    def add_attribute_model(self,
                            name,  # type: str
                            attr,  # type: AttributeModel
                            writeable_func=None,  # type: Optional[Callable]
                            ):
        # type: (...) -> AttributeModel
        return self._registry.add_attribute_model(
            self._part, name, attr, writeable_func)

    def report(self, info):
        # type: (Info) -> None
        callback = self._info_registry.reportable_infos[type(info)]
        callback(self._part, info)
