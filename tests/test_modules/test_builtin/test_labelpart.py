import unittest

from malcolm.core import Process, Put, Queue, Subscribe
from malcolm.modules.builtin.controllers import BasicController
from malcolm.modules.builtin.parts import LabelPart


class TestLabelPart(unittest.TestCase):
    def setUp(self):
        self.o = LabelPart(value="My label")
        self.p = Process("proc")
        self.c = BasicController("mri")
        self.c.add_part(self.o)
        self.p.add_controller(self.c)
        self.p.start()
        self.b = self.p.block_view(self.c.mri)

    def tearDown(self):
        self.p.stop(1)

    def test_init(self):
        assert self.o.name == "label"
        assert self.o.attr.value == "My label"
        assert self.o.attr.meta.tags == ["widget:textinput", "config:1"]
        assert self.b.meta.label == "My label"

    def test_setter(self):
        self.b.label.put_value("My label2")
        assert self.b.label.value == "My label2"
        assert self.b.meta.label == "My label2"

    def test_concurrency(self):
        q = Queue()
        # Subscribe to the whole block
        sub = Subscribe(id=0, path=["mri"], delta=True)
        sub.set_callback(q.put)
        self.c.handle_request(sub)
        # We should get first Delta through with initial value
        r = q.get().to_dict()
        assert r["id"] == 0
        assert len(r["changes"]) == 1
        assert len(r["changes"][0]) == 2
        assert r["changes"][0][0] == []
        assert r["changes"][0][1]["meta"]["label"] == "My label"
        assert r["changes"][0][1]["label"]["value"] == "My label"
        # Do a Put on the label
        put = Put(id=2, path=["mri", "label", "value"], value="New", get=True)
        put.set_callback(q.put)
        self.c.handle_request(put)
        # Check we got two updates before the return
        r = q.get().to_dict()
        assert r["id"] == 0
        assert len(r["changes"]) == 2
        assert len(r["changes"][0]) == 2
        assert r["changes"][0][0] == ["label", "value"]
        assert r["changes"][0][1] == "New"
        assert len(r["changes"][0]) == 2
        assert r["changes"][1][0] == ["label", "timeStamp"]
        r = q.get().to_dict()
        assert r["id"] == 0
        assert len(r["changes"]) == 1
        assert len(r["changes"][0]) == 2
        assert r["changes"][0][0] == ["meta", "label"]
        assert r["changes"][0][1] == "New"
        # Then the return
        r3 = q.get().to_dict()
        assert r3["id"] == 2
        assert r3["value"] == "New"
