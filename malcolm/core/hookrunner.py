from malcolm.core.loggable import Loggable
from malcolm.core.methodmeta import MethodMeta
from malcolm.core.errors import AbortedError


class HookRunner(Loggable):
    def __init__(self, hook_queue, part, func_name, task, *args, **params):
        self.set_logger_name("HookRunner(%s)" % part.name)
        self.hook_queue = hook_queue
        self.part = part
        self.task = task
        self.args = args
        self.func = getattr(part, func_name)
        self.filtered_params = {}
        self.method_meta = part.method_metas.get(func_name, None)
        if self.method_meta is None:
            self.method_meta = MethodMeta()
            self.method_meta.set_logger_name("MethodMeta")
        for k, v in params.items():
            if k in self.method_meta.takes.elements:
                self.filtered_params[k] = v

    def task_return(self):
        try:
            result = self.method_meta.call_post_function(
                self.func, self.filtered_params, self.task, *self.args)
        except AbortedError as e:
            self.log_info("%s has been aborted", self.func)
            result = e
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception(
                "%s %s raised exception", self.func, self.filtered_params)
            result = e
        self.log_debug("Putting %r on queue", result)
        self.hook_queue.put((self.part, result))

    def start(self):
        self.task.define_spawn_function(self.task_return)
        sentinel_stop = object()
        self.task.sentinel_stop = sentinel_stop
        # Say that we should only listen to stops after this point
        self.task.q.put(sentinel_stop)
        self.task.start()

    def stop(self):
        self.task.stop()

    def wait(self):
        self.task.wait()
