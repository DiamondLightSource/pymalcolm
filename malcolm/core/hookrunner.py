from malcolm.core.loggable import Loggable
from malcolm.core.errors import AbortedError


class HookRunner(Loggable):
    def __init__(self, hook_queue, part, func, context, args):
        self.set_logger_extra(part=part.name)
        self.hook_queue = hook_queue
        self.part = part
        self.func = func
        self.context = context
        self.args = args
        self.spawned = self.part.spawn(self.func_result_on_queue)

    def func_result_on_queue(self):
        try:
            result = self.func(self.context, *self.args)
        except AbortedError as e:
            self.log.info("%s has been aborted", self.func)
            result = e
        except Exception as e:  # pylint:disable=broad-except
            self.log.exception(
                "%s%s raised exception %s", self.func, self.args, e)
            result = e
        self.hook_queue.put((self.part, result))

    def stop(self):
        self.context.stop()

    def wait(self, timeout=None):
        self.spawned.wait(timeout=timeout)
