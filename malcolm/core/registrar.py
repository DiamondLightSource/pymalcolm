from annotypes import WithCallTypes, TYPE_CHECKING, Anno

from .hook import Hook
from .models import AttributeModel, MethodModel
from .info import Info
from .registry import Registry
from .part import Part

if TYPE_CHECKING:
    from typing import Optional, Dict, Callable, Type, Tuple


class Registrar(object):
    def __init__(self, registry, part):
        # type: (Registry, Part) -> None
        self.registry = registry
        self.part = part

    def add_method_model(self,
                         func,  # type: Callable
                         name=None,  # type: Optional[str]
                         description=None,  # type: Optional[str]
                         call_types=None,  # type: Optional[Dict[str, Anno]]
                         ):
        # type: (...) -> MethodModel
        """Register a function to be added to the block"""
        if name is None:
            name = func.__name__
        if description is None:
            description = func.__doc__
        if call_types is None:
            call_types = getattr(func, "call_types", None)
        method = MethodModel()
        self.registry.add_field(self.part, name, method, func)
        return method

    def add_attribute_model(self,
                            name,  # type: str
                            attr,  # type: AttributeModel
                            writeable_func=None,  # type: Optional[Callable]
                            ):
        # type: (...) -> AttributeModel
        self.registry.add_field(self.part, name, attr, writeable_func)
        return attr

    def attach_to_hook(self, func, *hooks, **kwargs):
        # type: (Callable, *Type[Hook], **Dict[str, Anno]) -> None
        call_types = kwargs.get("call_types", None)
        if call_types is None:
            call_types = getattr(func, "call_types", {})
        for hook in hooks:
            self.registry.attach_to_hook(
                self.part, func, call_types, hook)

    def report(self, info):
        # type: (Info) -> None
        self.registry.report(self.part, info)
