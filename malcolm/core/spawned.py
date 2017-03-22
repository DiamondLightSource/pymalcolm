import logging

from malcolm.compat import maybe_import_cothread


class Spawned(object):
    def __init__(self, function, args, kwargs, use_cothread, thread_pool=None):
        def catching_function():
            try:
                function(*args, **kwargs)
            except Exception:
                # Should only get this far in badly written code. What should
                # actually happen is that function should have the try catch
                logging.exception(
                    "Exception calling %s(*%s, **%s)", function, args, kwargs)

        if use_cothread:
            self.cothread = maybe_import_cothread()
        else:
            self.cothread = None
        if self.cothread:
            self._spawn = self.cothread.Spawn(catching_function)
            self._spawn_ready = False
        else:
            self._apply_result = thread_pool.apply_async(catching_function)

    def wait(self, timeout=None):
        if self.cothread:
            if not self._spawn_ready:
                self._spawn.Wait(timeout)
                self._spawn_ready = True
        else:
            self._apply_result.wait(timeout)

    def ready(self):
        if self.cothread:
            if self._spawn_ready:
                return True
            else:
                return bool(self._spawn)
        else:
            return self._apply_result.ready()
