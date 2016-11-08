from malcolm.core import Spawnable


class CothreadImporter(Spawnable):
    instance = None
    cothread = None
    catools = None

    def __init__(self, process):
        self.process = process
        self.q = process.create_queue()
        self.event = None
        self.add_spawn_function(self.import_cothread, self.stop_cothread)

    def import_cothread(self):
        import cothread
        from cothread import catools
        from cothread.input_hook import _install_readline_hook
        _install_readline_hook(None)
        self.event = cothread.Event()
        self.q.put((cothread, catools))
        self.event.Wait()

    def stop_cothread(self):
        self.event.Signal()

    @classmethod
    def get_cothread(cls, process):
        if cls.instance is None:
            cls.instance = CothreadImporter(process)
            cls.instance.start()
            cls.cothread, cls.catools = cls.instance.q.get()
        return cls.cothread, cls.catools
