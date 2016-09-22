import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
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
from malcolm.controllers.defaultcontroller import DefaultController
from malcolm.core import Process, SyncFactory, Task, ClientController
from malcolm.comms.websocket import WebsocketServerComms, WebsocketClientComms
from malcolm.parts.demo import HelloPart, CounterPart


class TestSystemWSCommsServerOnly(unittest.TestCase):
    socket = 8881

    def setUp(self):
        self.sf = SyncFactory("sync")
        self.process = Process("proc", self.sf)
        part = HelloPart(self.process, None)
        DefaultController("hello", self.process, parts={"hello":part})
        WebsocketServerComms(self.process, dict(port=self.socket))
        self.process.start()

    def tearDown(self):
        self.process.stop()

    @gen.coroutine
    def send_message(self):
        conn = yield websocket_connect("ws://localhost:%s/ws" % self.socket)
        req = dict(
            type="malcolm:core/Post:1.0",
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
            type="malcolm:core/Return:1.0",
            value=dict(
                greeting="Hello me"
            )
        ))
        conn.close()

    def test_server_and_simple_client(self):
        self.send_message()


class TestSystemWSCommsServerAndClient(unittest.TestCase):
    socket = 8882

    def setUp(self):
        self.sf = SyncFactory("sync")
        self.process = Process("proc", self.sf)
        DefaultController("hello", self.process, parts=dict(
            hello=HelloPart(self.process, None)))
        DefaultController("counter", self.process, parts=dict(
            counter=CounterPart(self.process, None)))
        WebsocketServerComms(self.process, dict(port=self.socket))
        self.process.start()
        self.process2 = Process("proc2", self.sf)
        WebsocketClientComms(self.process2,
                             dict(hostname="localhost", port=self.socket))
        self.process2.start()

    def tearDown(self):
        self.process.stop()
        self.process2.stop()
        self.socket += 1

    def test_server_hello_with_malcolm_client(self):
        block2 = ClientController('hello', self.process2).block
        task = Task("task", self.process2)
        futures = task.when_matches(block2["state"], "Ready")
        task.wait_all(futures, timeout=1)
        ret = block2.say_hello("me2")
        self.assertEqual(ret, dict(greeting="Hello me2"))

    def test_server_counter_with_malcolm_client(self):
        block2 = ClientController('counter', self.process2).block
        task = Task("task", self.process2)
        futures = task.when_matches(block2["state"], "Ready")
        task.wait_all(futures, timeout=1)
        self.assertEqual(block2.counter, 0)
        block2.increment()
        self.assertEqual(block2.counter, 1)

if __name__ == "__main__":
    unittest.main(verbosity=2)
