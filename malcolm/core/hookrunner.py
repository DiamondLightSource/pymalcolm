import weakref

from malcolm.core.loggable import Loggable
from malcolm.core.errors import AbortedError


class HookRunner(Loggable):
    def __init__(self, hook_queue, part, func, context, args):
        self.set_logger_name("HookRunner(%s)" % part.name)
        self.hook_queue = hook_queue
        self.part = part
        self.func = func
        # context might have been aborted but have nothing servicing the queue,
        # we still want the legitimate messages on the queue so just tell it
        # to ignore stops
        context.ignore_stops_before_now()
        self.context = context
        self.args = args
        self.spawned = self.part.spawn(self.func_result_on_queue)

    def func_result_on_queue(self):
        try:
            result = self.func(self.context, *self.args)
        except AbortedError as e:
            self.log_info("%s has been aborted", self.func)
            result = e
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("%s%s raised exception", self.func, self.args)
            result = e
        self.log_debug("Putting %r on queue", result)
        self.hook_queue.put((self.part, result))

    def stop(self):
        self.context.stop()

    def wait(self):
        self.spawned.wait()
