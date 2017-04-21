import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))


import multiprocessing
import unittest


# module imports


def p1(q):
    import logging
    logging.basicConfig(level=logging.DEBUG)
    from malcolm.core import Process, call_with_params, Context
    from malcolm.blocks.demo import hello_block, counter_block
    from malcolm.blocks.pva import pva_server_block
    process = Process("proc")
    call_with_params(hello_block, process, mri="hello")
    call_with_params(counter_block, process, mri="counter2")
    call_with_params(pva_server_block, process, mri="server")
    context = Context(process)
    process.start()
    while True:
        try:
            q.get(timeout=0.01)
        except Exception as e:
            context.sleep(0.1)
        else:
            process.stop()
            return


class TestSystemPVACommsServerAndClient(unittest.TestCase):

    def setUp(self):
        self.mp_q = multiprocessing.Queue()
        self.mp = multiprocessing.Process(target=p1, args=(self.mp_q,))
        self.mp.start()
        from malcolm.core import Process, call_with_params
        from malcolm.blocks.pva import pva_client_block
        self.process2 = Process("proc2")
        self.client = call_with_params(
            pva_client_block, self.process2, mri="client")
        self.process2.start()

    def tearDown(self):
        self.process2.stop()
        self.mp_q.put(None)
        self.mp.join()

    def s_server_hello_with_malcolm_client(self):
        from malcolm.core import call_with_params, Context, ResponseError
        from malcolm.blocks.builtin import proxy_block
        call_with_params(
            proxy_block, self.process2, mri="hello", comms="client")
        context = Context(self.process2)
        context.when_matches(["hello", "health", "value"], "OK", timeout=2)
        block2 = self.process2.block_view("hello")
        ret = block2.greet(name="me2")
        assert ret == dict(greeting="Hello me2")
        with self.assertRaises(ResponseError):
            block2.error()

    #def test_server_counter_with_malcolm_client(self):
    #    from malcolm.core import call_with_params, Context
    #    from malcolm.blocks.builtin import proxy_block
    #    call_with_params(
    #        proxy_block, self.process2, mri="counter2", comms="client")
    #    context = Context("context", self.process2)
    #    context.when_matches(["counter2", "health", "value"], "OK", timeout=2)
    #    context.sleep(3)
    #    block2 = self.process2.block_view("counter2")
    #    block2.zero()
    #    self.assertEqual(block2.counter.value, 0)
    #    block2.increment()
    #    self.assertEqual(block2.counter.value, 1)
    #    block2.zero()
    #    self.assertEqual(block2.counter.value, 0)
    #    assert self.client.remote_blocks.value == (
    #        "hello", "counter", "server")


if __name__ == "__main__":
    from malcolm.core import Queue
    q = Queue()
    p1(q)
