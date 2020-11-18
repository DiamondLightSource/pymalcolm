import json
import unittest
from sys import version_info

import cothread
from annotypes import json_encode
from tornado import gen
from tornado.websocket import websocket_connect

from malcolm.compat import OrderedDict
from malcolm.core import Post, Process, Queue, ResponseError
from malcolm.modules.builtin.blocks import proxy_block
from malcolm.modules.demo.blocks import counter_block, hello_block
from malcolm.modules.web.blocks import web_server_block, websocket_client_block
from malcolm.modules.web.util import IOLoopHelper


class TestSystemWSCommsServerOnly(unittest.TestCase):
    socket = 8881

    def setUp(self):
        self.process = Process("proc")
        self.hello = hello_block(mri="hello")[-1]
        self.process.add_controller(self.hello)
        self.server = web_server_block(mri="server", port=self.socket)[-1]
        self.process.add_controller(self.server)
        self.result = Queue()
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=1)

    @gen.coroutine
    def send_messages(self, messages, convert_json=True):
        conn = yield websocket_connect("ws://localhost:%s/ws" % self.socket)
        num = len(messages)
        for msg in messages:
            if convert_json:
                msg = json_encode(msg)
            conn.write_message(msg)
        for _ in range(num):
            resp = yield conn.read_message()
            resp = json.loads(resp)
            cothread.Callback(self.result.put, resp)
        conn.close()

    @gen.coroutine
    def send_message(self, req, convert_json=True):
        yield self.send_messages([req], convert_json)

    def test_server_and_simple_client(self):
        msg = OrderedDict()
        msg["typeid"] = "malcolm:core/Post:1.0"
        msg["id"] = 0
        msg["path"] = ("hello", "greet")
        msg["parameters"] = dict(name="me")
        IOLoopHelper.call(self.send_message, msg)
        resp = self.result.get(timeout=2)
        assert resp == dict(typeid="malcolm:core/Return:1.0", id=0, value="Hello me")

    def test_concurrency(self):
        msg1 = Post(
            id=0, path=["hello", "greet"], parameters=dict(name="me", sleep=2)
        ).to_dict()
        msg2 = Post(id=1, path=["hello", "error"]).to_dict()
        IOLoopHelper.call(self.send_messages, [msg1, msg2])
        resp = self.result.get(timeout=1)
        assert resp == dict(
            typeid="malcolm:core/Error:1.0",
            id=1,
            message="RuntimeError: You called method error()",
        )
        resp = self.result.get(timeout=3)
        assert resp == dict(typeid="malcolm:core/Return:1.0", id=0, value="Hello me")

    def test_blocks_delta(self):
        msg = OrderedDict()
        msg["typeid"] = "malcolm:core/Subscribe:1.0"
        msg["id"] = 0
        msg["path"] = (".", "blocks", "value")
        msg["delta"] = True
        IOLoopHelper.call(self.send_message, msg)
        resp = self.result.get(timeout=2)
        assert resp == dict(
            typeid="malcolm:core/Delta:1.0",
            id=0,
            changes=[
                [
                    [],
                    {
                        "label": ["hello", "server"],
                        "mri": ["hello", "server"],
                        "typeid": "malcolm:core/Table:1.0",
                    },
                ]
            ],
        )

    def test_blocks_update(self):
        msg = OrderedDict()
        msg["typeid"] = "malcolm:core/Subscribe:1.0"
        msg["id"] = 0
        msg["path"] = (".", "blocks", "value", "mri")
        msg["delta"] = False
        IOLoopHelper.call(self.send_message, msg)
        resp = self.result.get(timeout=2)
        assert resp == dict(
            typeid="malcolm:core/Update:1.0", id=0, value=["hello", "server"]
        )

    def test_error_server_and_simple_client_badJSON(self):
        IOLoopHelper.call(self.send_message, "I am JSON (but not a dict)")
        resp = self.result.get(timeout=2)
        assert resp == dict(
            typeid="malcolm:core/Error:1.0",
            id=-1,
            message=(
                "ValueError: Error decoding JSON object "
                "(didn't return FrozenOrderedDict)"
            ),
        )

        IOLoopHelper.call(self.send_message, "I am not JSON", convert_json=False)
        resp = self.result.get(timeout=2)
        if version_info[0] == 2:
            assert resp == dict(
                typeid="malcolm:core/Error:1.0",
                id=-1,
                message=(
                    "ValueError: Error decoding JSON object "
                    "(No JSON object could be decoded)"
                ),
            )
        elif version_info[0] == 3:
            assert resp == dict(
                typeid="malcolm:core/Error:1.0",
                id=-1,
                message=(
                    "ValueError: Error decoding JSON object "
                    "(Expecting value: line 1 column 1 (char 0))"
                ),
            )
        else:
            raise Exception("Got bad python version info")

    def test_error_server_and_simple_client_no_id(self):
        msg = OrderedDict()
        msg["typeid"] = "malcolm:core/Post:1.0"
        msg["path"] = ("hello", "greet")
        msg["parameters"] = dict(name="me")
        IOLoopHelper.call(self.send_message, msg)
        resp = self.result.get(timeout=2)
        assert resp == dict(
            typeid="malcolm:core/Error:1.0",
            id=-1,
            message="FieldError: id field not present in JSON message",
        )

    def test_error_server_and_simple_client_bad_type(self):
        msg = OrderedDict()
        msg["typeid"] = "NotATypeID"
        msg["id"] = 0
        msg["path"] = ("hello", "greet")
        msg["parameters"] = dict(name="me")
        IOLoopHelper.call(self.send_message, msg)
        resp = self.result.get(timeout=2)
        assert resp == dict(
            typeid="malcolm:core/Error:1.0",
            id=0,
            message="TypeError: 'NotATypeID' not a valid typeid",
        )

    def test_error_server_and_simple_client_no_type(self):
        msg = OrderedDict()
        msg["id"] = 0
        msg["path"] = ("hello", "greet")
        msg["parameters"] = dict(name="me")
        IOLoopHelper.call(self.send_message, msg)
        resp = self.result.get(timeout=2)

        if version_info[0] == 2:
            message = (
                "TypeError: typeid not present in keys "
                + "[u'id', u'path', u'parameters']"
            )
        elif version_info[0] == 3:
            message = (
                "TypeError: typeid not present in keys "
                + "['id', 'path', 'parameters']"
            )
        else:
            raise Exception("Got bad python version info")
        assert resp == dict(typeid="malcolm:core/Error:1.0", id=0, message=message)

    def test_error_server_and_simple_client_bad_path_controller(self):
        msg = OrderedDict()
        msg["typeid"] = "malcolm:core/Post:1.0"
        msg["id"] = 0
        msg["path"] = ("goodbye", "insult")
        msg["parameters"] = dict(name="me")
        IOLoopHelper.call(self.send_message, msg)
        resp = self.result.get(timeout=2)
        assert resp == dict(
            typeid="malcolm:core/Error:1.0",
            id=0,
            message="ValueError: No controller registered for mri 'goodbye'",
        )

    def test_error_server_and_simple_client_superfluous_params(self):
        msg = OrderedDict()
        msg["typeid"] = "malcolm:core/Get:1.0"
        msg["id"] = 0
        msg["path"] = ("hello", "meta")
        msg["parameters"] = dict(name="me")
        IOLoopHelper.call(self.send_message, msg)
        resp = self.result.get(timeout=2)
        assert resp == dict(
            typeid="malcolm:core/Error:1.0",
            id=0,
            message="TypeError: malcolm:core/Get:1.0 raised error: "
            + "__init__() got an unexpected keyword argument 'parameters'",
        )

    def test_error_server_and_simple_client_bad_path_dict_attribute(self):
        msg = OrderedDict()
        msg["typeid"] = "malcolm:core/Get:1.0"
        msg["id"] = 0
        msg["path"] = ("hello", "greet", "meta", "takes", "elements", "bad")
        IOLoopHelper.call(self.send_message, msg)
        resp = self.result.get(timeout=2)
        assert resp == dict(
            typeid="malcolm:core/Error:1.0",
            id=0,
            message=(
                "UnexpectedError: Object 'hello.greet.meta.takes.elements' "
                "of type %r has no attribute 'bad'"
            )
            % type(OrderedDict()),
        )

    def test_error_server_and_simple_client_bad_path_attribute(self):
        msg = OrderedDict()
        msg["typeid"] = "malcolm:core/Get:1.0"
        msg["id"] = 0
        msg["path"] = ("hello", "meat")
        IOLoopHelper.call(self.send_message, msg)
        resp = self.result.get(timeout=2)
        assert resp == dict(
            typeid="malcolm:core/Error:1.0",
            id=0,
            message=(
                "UnexpectedError: Object 'hello' of type "
                "'malcolm:core/Block:1.0' has no attribute 'meat'"
            ),
        )

    def test_error_server_and_simple_client_no_path(self):
        msg = OrderedDict()
        msg["typeid"] = "malcolm:core/Post:1.0"
        msg["id"] = 0
        IOLoopHelper.call(self.send_message, msg)
        resp = self.result.get(timeout=2)
        assert resp == dict(
            typeid="malcolm:core/Error:1.0",
            id=0,
            message="ValueError: Expected a path with at least 1 element, got []",
        )


class TestSystemWSCommsServerAndClient(unittest.TestCase):
    socket = 8883

    def setUp(self):
        self.process = Process("proc")
        for controller in (
            hello_block(mri="hello")
            + counter_block(mri="counter")
            + web_server_block(mri="server", port=self.socket)
        ):
            self.process.add_controller(controller)
        self.process.start()
        self.process2 = Process("proc2")
        for controller in (
            websocket_client_block(mri="client", port=self.socket)
            + proxy_block(mri="hello", comms="client")
            + proxy_block(mri="counter", comms="client")
        ):
            self.process2.add_controller(controller)
        self.process2.start()

    def tearDown(self):
        self.socket += 1
        self.process.stop(timeout=1)
        self.process2.stop(timeout=1)

    def test_server_hello_with_malcolm_client(self):
        block2 = self.process2.block_view("hello")
        ret = block2.greet("me2")
        assert ret == "Hello me2"
        with self.assertRaises(ResponseError):
            block2.error()

    def test_server_counter_with_malcolm_client(self):
        block1 = self.process.block_view("counter")
        block2 = self.process2.block_view("counter")
        assert block2.counter.value == 0
        block2.increment()
        assert block2.counter.timeStamp.to_time() == block1.counter.timeStamp.to_time()
        assert block2.counter.value == 1
        block2.zero()
        assert block2.counter.value == 0
        assert self.process2.block_view("client").remoteBlocks.value.mri == [
            "hello",
            "counter",
            "server",
        ]

    def test_server_blocks(self):
        block = self.process.block_view("server")
        assert block.blocks.value.mri == ["hello", "counter", "server"]
        assert block.blocks.value.label == ["hello", "counter", "server"]
        assert block.blocks.meta.writeable is False
