from annotypes import Anno, TYPE_CHECKING

from malcolm.compat import OrderedDict
from .queue import Queue
from .hook import Hookable
from .info import Info
from .spawned import Spawned
from .models import MethodModel, AttributeModel

if TYPE_CHECKING:
    from typing import Union, List, Tuple, Dict, Callable, Optional, Type
    Field = Union[AttributeModel, MethodModel]
    FieldDict = Dict[object, List[Tuple[str, Field, Callable]]]
    Callback = Callable[[object, Info], None]

with Anno("The name of the Part within the Controller"):
    APartName = str


class FieldRegistry(object):
    def __init__(self):
        # type: () -> None
        self.fields = OrderedDict()  # type: FieldDict

    def get_field(self, name):
        # type: (str) -> Field
        for _, (n, field, _) in self.fields.items():
            if n == name:
                return field
        raise ValueError("No field named %s found" % (name,))

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
        method = MethodModel.from_callable(func, description)
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
    def __init__(self, spawn):
        # type: (Callable[..., Spawned]) -> None
        self._reportable_infos = {}  # type: Dict[Type[Info], Callback]
        self._spawn = spawn
        self._report_queue = Queue()

    def add_reportable(self, info, callback):
        # type: (Type[Info], Callback) -> None
        self._reportable_infos[info] = callback

    def report(self, reporter, info):
        # type: (object, Info) -> None
        callback = self._reportable_infos[type(info)]
        self._report_queue.put((callback, reporter, info))
        # Spawn in case we are coming from a non-cothread to cothread thread
        self._spawn(self._report).wait()

    def _report(self):
        callback, reporter, info = self._report_queue.get()
        callback(reporter, info)


class Part(Hookable):
    def __init__(self, name):
        # type: (APartName) -> None
        self.set_logger(name=name)
        self.name = name

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        """Use the given Registrar to populate the hooks and fields"""
        raise NotImplementedError()


class PartRegistrar(object):
    def __init__(self, field_registry, info_registry, part):
        # type: (FieldRegistry, InfoRegistry, Part]) -> None
        self._field_registry = field_registry
        self._info_registry = info_registry
        self._part = part
        self._info_queue = Queue()

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
        self._info_registry.report(self._part, info)
