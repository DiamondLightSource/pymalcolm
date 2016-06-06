import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# tornado
from pkg_resources import require
require("tornado")
from tornado.websocket import websocket_connect
from tornado import gen
from tornado.ioloop import IOLoop
import json


# module imports
from malcolm.controllers.hellocontroller import HelloController
from malcolm.core.block import Block
from malcolm.core.process import Process
from malcolm.core.syncfactory import SyncFactory
from malcolm.core.request import Request
from malcolm.wscomms.wsservercomms import WSServerComms


class TestSystemWSComms(unittest.TestCase):
    def setUp(self):
        sync_factory = SyncFactory("sync")
        self.process = Process("proc", sync_factory)
        block = Block("hello")
        self.process.add_block(block)
        HelloController(block)
        self.sc = WSServerComms("sc", self.process, 8888)
        self.process.start()
        self.sc.start()

    def tearDown(self):
        self.sc.stop()
        self.process.stop()

    @gen.coroutine
    def send_message(self):
        conn = yield websocket_connect("ws://localhost:8888/ws")
        req = dict(
            type="Post",
            id=0,
            endpoint=["hello", "say_hello"],
            parameters=dict(
                name="me"
            )
        )
        conn.write_message(json.dumps(req))
        resp = yield conn.read_message()
        resp = json.loads(resp)
        self.assertEqual(resp, dict(
            id=0,
            type="Return",
            value=dict(
                greeting="Hello me"
            )
        ))
        conn.close()

    def test_server_runs_standalone(self):
        IOLoop.current().run_sync(self.send_message)

if __name__ == "__main__":
    unittest.main(verbosity=2)
