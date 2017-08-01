import threading

from malcolm.core import Queue
from malcolm.compat import maybe_import_cothread


def _import_cothread(q):
    import cothread
    from cothread import catools
    from cothread.input_hook import _install_readline_hook
    _install_readline_hook(None)
    q.put((cothread, catools))
    # Wait forever
    cothread.Event().Wait()


class CaToolsHelper(object):
    _instance = None

    def __init__(self):
        assert not self._instance, \
            "Can't create more than one instance of Singleton. Use instance()"
        self.cothread = maybe_import_cothread()
        if self.cothread:
            # We can use it in this thread
            from cothread import catools
            self.in_cothread_thread = True
        else:
            # We need our own thread to run it in
            q = Queue()
            threading.Thread(target=_import_cothread, args=(q,)).start()
            self.cothread, catools = q.get()
            self.in_cothread_thread = False
        self.catools = catools
        self.DBR_STRING = catools.DBR_STRING
        self.DBR_LONG = catools.DBR_LONG
        self.DBR_DOUBLE = catools.DBR_DOUBLE
        self.FORMAT_CTRL = catools.FORMAT_CTRL
        self.FORMAT_TIME = catools.FORMAT_TIME
        self.DBR_ENUM = catools.DBR_ENUM
        self.DBR_CHAR_STR = catools.DBR_CHAR_STR

    def caget(self, *args, **kwargs):
        if self.in_cothread_thread:
            return self.catools.caget(*args, **kwargs)
        else:
            return self.cothread.CallbackResult(
                self.catools.caget, *args, **kwargs)

    def caput(self, *args, **kwargs):
        if self.in_cothread_thread:
            return self.catools.caput(*args, **kwargs)
        else:
            return self.cothread.CallbackResult(
                self.catools.caput, *args, **kwargs)

    def camonitor(self, *args, **kwargs):
        if self.in_cothread_thread:
            return self.catools.camonitor(*args, **kwargs)
        else:
            return self.cothread.CallbackResult(
                self.catools.camonitor, *args, **kwargs)

    @classmethod
    def instance(cls):
        if not cls._instance:
            cls._instance = CaToolsHelper()
        return cls._instance

