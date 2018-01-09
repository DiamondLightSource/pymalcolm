from annotypes import TYPE_CHECKING, Anno

from .hook import Hook
from .models import AttributeModel, MethodModel
from .info import Info
from .part import Part

if TYPE_CHECKING:
    from typing import Dict, Callable, Type, Tuple, Union, List
    Field = Union[AttributeModel, MethodModel]
    CallTypes = Dict[str, Anno]
    Hooked = Tuple[Callable[..., List[Info]], CallTypes]
    Callback = Callable[[Part, Info], None]


class Registry(object):
    def __init__(self, hooks):
        # type: (List[Type[Hook]]) -> None
        self.runnable_hooks = hooks
        self.reportable_infos = {}  # type: Dict[Type[Info], Callback]
        self.hooked = {}  # type: Dict[Tuple[Part, Type[Hook]], Hooked]

    def add_reportable(self, info, callback):
        # type: (Type[Info], Callback) -> None
        self.reportable_infos[info] = callback

    def add_field(self, part, name, model, writeable_func):
        # type: (Part, str, Field, Callable) -> None
        pass

    def attach_to_hook(self, part, func, call_types, hook):
        # type: (Part, Callable, CallTypes, Type[Hook]) -> None
        assert hook in self.runnable_hooks, \
            "%s is not in runnable hooks %s" % (hook, self.runnable_hooks)
        key = (part, hook)
        assert key not in self.hooked, \
            "%s already hooked to %s" % (key, self.hooked[key])
        self.hooked[(part, hook)] = (func, call_types)

    def report(self, part, info):
        # type: (Part, Info) -> None
        callback = self.reportable_infos[type(info)]
        callback(part, info)

    def get_hooked(self, part, hook):
        # type: (Part, Hook) -> Hooked
        return self.hooked[(part, type(hook))]


