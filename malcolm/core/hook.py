import logging
import weakref

from annotypes import WithCallTypes, Anno, Any, TYPE_CHECKING

from malcolm.compat import queue
from .errors import AbortedError
from .part import Part
from .context import Context

if TYPE_CHECKING:
    from typing import Callable, Dict


with Anno("The part that has attached to the Hook"):
    APart = Part
with Anno("Context that should be used to perform operations on child blocks"):
    AContext = Context

# Create a module level logger
log = logging.getLogger(__name__)


class Hook(WithCallTypes):
    def __init__(self, part, context, **kwargs):
        # type: (APart, AContext, **Any) -> None
        self.part = part
        self.context = weakref.proxy(context)
        self.kwargs = kwargs

    @property
    def name(self):
        return type(self).__name__

    def run(self, func, call_types, hook_queue):
        # type: (Callable[..., Any], Dict[str, Anno], queue.Queue) -> None
        try:
            args = {k: self.kwargs[k] for k in call_types}
            result = func(**args)
        except AbortedError as e:
            log.info("%s: %s has been aborted", self.part.name, self.func)
            result = e
        except Exception as e:  # pylint:disable=broad-except
            log.exception(
                "%s: %s%s raised exception %s",
                self.part.name, self.func, self.args, e)
            result = e
        hook_queue.put((self.part, result))
