from threading import Thread

from tornado.ioloop import IOLoop


class IOLoopHelper(object):
    _loop = None  # type: IOLoop

    @classmethod
    def loop(cls):
        if cls._loop is None:
            loop = IOLoop.current()
            cls._loop = loop
            t = Thread(target=loop.start)
            t.setDaemon(True)
            t.start()
        return cls._loop

    @classmethod
    def call(cls, func, *args, **kwargs):
        cls.loop().add_callback(func, *args, **kwargs)
