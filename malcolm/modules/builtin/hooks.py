import weakref

from annotypes import Anno, TYPE_CHECKING, Any

from malcolm.core import Hook, Part, Context, Info

with Anno("The part that has attached to the Hook"):
    APart = Part
with Anno("Context that should be used to perform operations on child blocks"):
    AContext = Context


if TYPE_CHECKING:
    from typing import List, Callable


class ControllerHook(Hook):
    """A hook that takes Part and Context for use in controllers"""
    def __init__(self, part, context, **kwargs):
        # type: (APart, AContext, **Any) -> None
        self.context = weakref.proxy(context)
        super(ControllerHook, self).__init__(
            part, context=self.context, **kwargs)

    def run(self, func):
        # type: (Callable[..., List[Info]]) -> None
        # context might have been aborted but have nothing servicing
        # the queue, we still want the legitimate messages on the
        # queue so just tell it to ignore stops it got before now
        self.context.ignore_stops_before_now()
        super(ControllerHook, self).run(func)

    def stop(self):
        self.context.stop()


class InitHook(ControllerHook):
    """Called when this controller is told to start by the process"""
    def __init__(self, part, context):
        # type: (APart, AContext) -> None
        super(InitHook, self).__init__(**locals())


class ResetHook(ControllerHook):
    """Called at reset() to reset all parts to a known good state"""
    def __init__(self, part, context):
        # type: (APart, AContext) -> None
        super(ResetHook, self).__init__(**locals())


class HaltHook(ControllerHook):
    """Called when this controller is told to halt"""
    def __init__(self, part, context):
        # type: (APart, AContext) -> None
        super(HaltHook, self).__init__(**locals())


class DisableHook(ControllerHook):
    """Called at disable() to stop all parts updating their attributes"""
    def __init__(self, part, context):
        # type: (APart, AContext) -> None
        super(DisableHook, self).__init__(**locals())


class LayoutHook(ControllerHook):
    """Called when layout table set and at init to update child layout"""
    def __init__(self, part, context, ports, layout):
        # type: (APart, AContext, APortMap, ALayoutTable) -> None
        super(LayoutHook, self).__init__(**locals())
