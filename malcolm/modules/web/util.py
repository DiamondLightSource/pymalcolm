import asyncio
import atexit
from threading import Thread
from typing import Optional, Union

from annotypes import Anno, Array
from tornado.ioloop import IOLoop

from malcolm.core import Table


class IOLoopHelper:
    _loop: Optional[IOLoop] = None
    _thread: Optional[Thread] = None

    @classmethod
    def loop(cls):
        if cls._loop is None:
            asyncio.set_event_loop(asyncio.new_event_loop())
            loop = IOLoop.current()
            cls._loop = loop

            def run():
                loop.start()
                # loop.stop() called from somewhere else
                loop.close()

            cls._thread = Thread(target=run)
            cls._thread.setDaemon(True)
            cls._thread.start()
            atexit.register(cls.stop)
        return cls._loop

    @classmethod
    def call(cls, func, *args, **kwargs):
        cls.loop().add_callback(func, *args, **kwargs)

    @classmethod
    def stop(cls):
        if cls._loop is not None:
            # Remove cls._loop so all other stop() methods are no-ops
            loop = cls._loop
            cls._loop = None
            loop.add_callback(loop.stop)
            # Wait until done
            cls._thread.join()
            cls._thread = None


with Anno("The Malcolm Resource Identifier for the Block"):
    AMris = Union[Array[str]]
with Anno("A human readable label for the Block"):
    ALabels = Union[Array[str]]


class BlockTable(Table):
    def __init__(self, mri: AMris, label: ALabels) -> None:
        self.mri = mri
        self.label = label
