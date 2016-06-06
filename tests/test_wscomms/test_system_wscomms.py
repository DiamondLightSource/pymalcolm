import unittest
import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# tornado
from tornado.websocket import websocket_connect
from tornado import gen
from tornado.ioloop import IOLoop
import json


# module imports
from malcolm.controllers.hellocontroller import HelloController
from malcolm.controllers.clientcontroller import ClientController
from malcolm.core.block import Block
from malcolm.core.process import Process
from malcolm.core.syncfactory import SyncFactory
from malcolm.core.request import Request
from malcolm.wscomms.wsservercomms import WSServerComms
from malcolm.wscomms.wsclientcomms import WSClientComms


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

    def test_server_and_simple_client(self):
        self.send_message()

    def test_server_with_malcolm_client(self):
        self.cc = WSClientComms("cc", self.process, "ws://localhost:8888/ws")
        self.cc.start()
        # Wait for comms to be connected
        while not self.cc.conn.done():
            time.sleep(0.001)
        # Don't add to process as we already have a block of that name
        block2 = Block("hello")
        ClientController(self.process, block2, self.cc)
        ret = block2.say_hello("me2")
        self.assertEqual(ret, dict(greeting="Hello me2"))
        self.cc.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
