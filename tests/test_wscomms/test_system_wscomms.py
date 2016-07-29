import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import time
# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

import unittest

# tornado
from tornado.websocket import websocket_connect
from tornado import gen
import json


# module imports
from malcolm.controllers.hellocontroller import HelloController
from malcolm.controllers.clientcontroller import ClientController
from malcolm.core.block import Block
from malcolm.core.process import Process
from malcolm.core.syncfactory import SyncFactory
from malcolm.wscomms.wsservercomms import WSServerComms
from malcolm.wscomms.wsclientcomms import WSClientComms


class TestSystemWSCommsServerOnly(unittest.TestCase):
    socket = 8881

    def setUp(self):
        self.sf = SyncFactory("sync")
        self.process = Process("proc", self.sf)
        block = Block()
        HelloController(self.process, block,'hello')
        self.sc = WSServerComms("sc", self.process, self.socket)
        self.process.start()
        self.sc.start()

    def tearDown(self):
        self.sc.stop()
        self.sc.wait()
        self.process.stop()


    @gen.coroutine
    def send_message(self):
        conn = yield websocket_connect("ws://localhost:%s/ws" % self.socket)
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


class TestSystemWSCommsServerAndClient(TestSystemWSCommsServerOnly):
    socket = 8882

    def setUp(self):
        super(TestSystemWSCommsServerAndClient, self).setUp()
        self.process2 = Process("proc2", self.sf)
        self.block2 = Block()
        ClientController(self.process2, self.block2, 'hello')
        self.cc = WSClientComms("cc", self.process2, "ws://localhost:%s/ws" %
                                self.socket)
        self.process2.start()
        self.cc.start()

    def tearDown(self):
        super(TestSystemWSCommsServerAndClient, self).tearDown()
        self.cc.stop()
        self.cc.wait()
        self.process2.stop()

    def test_server_with_malcolm_client(self):
        # Normally we would wait for it to be connected here, but it isn't
        # attached to a process so just sleep for a bit
        time.sleep(0.5)
        ret = self.block2.say_hello("me2")
        self.assertEqual(ret, dict(greeting="Hello me2"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
