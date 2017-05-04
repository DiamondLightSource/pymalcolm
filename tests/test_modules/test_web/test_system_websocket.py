import unittest
import json

from tornado.websocket import websocket_connect
from tornado import gen

from malcolm.core import Process, call_with_params, Queue, Context, \
    ResponseError
from malcolm.modules.builtin.blocks import proxy_block
from malcolm.modules.demo.blocks import hello_block, counter_block
from malcolm.modules.web.blocks import web_server_block, websocket_client_block


class TestSystemWSCommsServerOnly(unittest.TestCase):
    socket = 8881

    def setUp(self):
        self.process = Process("proc")
        self.hello = call_with_params(hello_block, self.process, mri="hello")
        self.server = call_with_params(
            web_server_block, self.process, mri="server", port=self.socket)
        self.result = Queue()
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=1)

    @gen.coroutine
    def send_message(self):
        conn = yield websocket_connect("ws://localhost:%s/ws" % self.socket)
        req = dict(
            typeid="malcolm:core/Post:1.0",
            id=0,
            path=["hello", "greet"],
            parameters=dict(
                name="me"
            )
        )
        conn.write_message(json.dumps(req))
        resp = yield conn.read_message()
        resp = json.loads(resp)
        self.result.put(resp)
        conn.close()

    def test_server_and_simple_client(self):
        self.server._loop.add_callback(self.send_message)
        resp = self.result.get(timeout=2)
        assert resp == dict(
            typeid="malcolm:core/Return:1.0",
            id=0,
            value=dict(
                typeid='malcolm:core/Map:1.0',
                greeting="Hello me",
            )
        )


class TestSystemWSCommsServerAndClient(unittest.TestCase):
    socket = 8883

    def setUp(self):
        self.process = Process("proc")
        self.hello = call_with_params(hello_block, self.process, mri="hello")
        self.counter = call_with_params(
            counter_block, self.process, mri="counter")
        self.server = call_with_params(
            web_server_block, self.process, mri="server", port=self.socket)
        self.process.start()
        self.process2 = Process("proc2")
        self.client = call_with_params(
            websocket_client_block, self.process2, mri="client",
            port=self.socket)
        self.process2.start()

    def tearDown(self):
        self.socket += 1
        self.process.stop(timeout=1)
        self.process2.stop(timeout=1)

    def test_server_hello_with_malcolm_client(self):
        call_with_params(
            proxy_block, self.process2, mri="hello", comms="client")
        block2 = self.process2.block_view("hello")
        ret = block2.greet("me2")
        assert ret == dict(greeting="Hello me2")
        with self.assertRaises(ResponseError):
            block2.error()

    def test_server_counter_with_malcolm_client(self):
        call_with_params(
            proxy_block, self.process2, mri="counter", comms="client")
        block2 = self.process2.block_view("counter")
        assert block2.counter.value == 0
        block2.increment()
        assert block2.counter.value == 1
        block2.zero()
        assert block2.counter.value == 0
        assert self.client.remote_blocks.value == (
            "hello", "counter", "server")
