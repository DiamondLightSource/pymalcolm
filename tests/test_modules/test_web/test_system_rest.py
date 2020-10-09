import unittest

import cothread
from annotypes import json_encode
from tornado import gen
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from malcolm.core import Process, Queue
from malcolm.modules.demo.blocks import hello_block
from malcolm.modules.web.blocks import web_server_block
from malcolm.modules.web.util import IOLoopHelper


class TestSystemRest(unittest.TestCase):
    socket = 8886

    def setUp(self):
        self.process = Process("proc")
        self.hello = hello_block(mri="hello")[-1]
        self.process.add_controller(self.hello)
        self.server = web_server_block(mri="server", port=self.socket)[-1]
        self.process.add_controller(self.server)
        self.result = Queue()
        self.http_client = AsyncHTTPClient()
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=1)

    @gen.coroutine
    def get(self, mri):
        result = yield self.http_client.fetch(
            "http://localhost:%s/rest/%s" % (self.socket, mri)
        )
        cothread.Callback(self.result.put, result)

    @gen.coroutine
    def post(self, mri, method, args):
        req = HTTPRequest(
            "http://localhost:%s/rest/%s/%s" % (self.socket, mri, method),
            method="POST",
            body=args,
        )
        result = yield self.http_client.fetch(req)
        cothread.Callback(self.result.put, result)

    def test_get_hello(self):
        IOLoopHelper.call(self.get, "hello")
        result = self.result.get(timeout=2)
        assert result.body.decode().strip() == json_encode(self.hello._block)

    def test_post_hello(self):
        IOLoopHelper.call(self.post, "hello", "greet", json_encode(dict(name="me")))
        result = self.result.get(timeout=2)
        assert result.body.decode().strip() == json_encode("Hello me")
