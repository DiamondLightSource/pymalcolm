import weakref

from annotypes import Anno, Any, Mapping, Sequence, Array, Union, TypeVar

from malcolm.core import Hook, Part, Context
from .infos import PortInfo, LayoutInfo
from .util import LayoutTable

with Anno("The part that has attached to the Hook"):
    APart = Part
with Anno("Context that should be used to perform operations on child blocks"):
    AContext = Context
with Anno("Whether this operation is taking place at init"):
    AInit = bool

T = TypeVar("T")


class ControllerHook(Hook[T]):
    """A hook that takes Part and Context for use in controllers"""
    def __init__(self, part, context, **kwargs):
        # type: (APart, AContext, **Any) -> None
        # Pass a weak reference to our children
        super(ControllerHook, self).__init__(
            part, context=weakref.proxy(context), **kwargs)
        # But hold a strong reference here to stop it disappearing
        self.context = context

    def prepare(self):
        # type: () -> None
        # context might have been aborted but have nothing servicing
        # the queue, we still want the legitimate messages on the
        # queue so just tell it to ignore stops it got before now
        self.context.ignore_stops_before_now()

    def stop(self):
        # type: () -> None
        self.context.stop()


class InitHook(ControllerHook[None]):
    """Called when this controller is told to start by the process"""


class ResetHook(ControllerHook[None]):
    """Called at reset() to reset all parts to a known good state"""


class HaltHook(ControllerHook[None]):
    """Called when this controller is told to halt"""


class DisableHook(ControllerHook[None]):
    """Called at disable() to stop all parts updating their attributes"""


with Anno("The PortInfos for all the parts"):
    APortMap = Mapping[str, Array[PortInfo]]
with Anno("A possibly partial set of changes to the layout table that "
          "should be acted on"):
    ALayoutTable = LayoutTable
with Anno("The current layout information"):
    ALayoutInfos = Array[LayoutInfo]
ULayoutInfos = Union[ALayoutInfos, Sequence[LayoutInfo], LayoutInfo, None]


class LayoutHook(ControllerHook[ULayoutInfos]):
    """Called when layout table set and at init to update child layout"""

    def __init__(self, part, context, ports, layout):
        # type: (APart, AContext, APortMap, ALayoutTable) -> None
        super(LayoutHook, self).__init__(
            part, context, ports=ports, layout=layout)

    def validate_return(self, ret):
        # type: (ULayoutInfos) -> ALayoutInfos
        """Check that all returned infos are LayoutInfos"""
        return ALayoutInfos(ret)


with Anno("The serialized structure to load"):
    AStructure = Mapping[str, Mapping]


class LoadHook(ControllerHook[None]):
    """Called at load() to load child settings from a structure"""

    def __init__(self, part, context, structure, init):
        # type: (APart, AContext, AStructure, AInit) -> None
        super(LoadHook, self).__init__(
            part, context, structure=structure, init=init)


class SaveHook(ControllerHook[AStructure]):
    """Called at save() to serialize child settings into a dict structure"""

    def validate_return(self, ret):
        # type: (AStructure) -> AStructure
        """Check that a serialized structure is returned"""
        assert isinstance(ret, dict), \
            "Expected a structure, got %r" % (ret,)
        return ret
