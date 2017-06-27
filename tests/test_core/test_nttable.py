from collections import OrderedDict
import unittest

from malcolm.modules.builtin.vmetas import TableMeta, StringArrayMeta
from malcolm.core import Table, NTTable, Alarm, TimeStamp


class TestSerialization(unittest.TestCase):

    def setUp(self):
        elements = OrderedDict()
        elements["foo"] = StringArrayMeta(label="Foo").to_dict()
        elements["bar"] = StringArrayMeta().to_dict()
        meta = OrderedDict()
        meta["typeid"] = "malcolm:core/TableMeta:1.0"
        meta["elements"] = elements
        meta["description"] = "desc"
        meta["tags"] = ()
        meta["writeable"] = True
        meta["label"] = "my label"
        value = OrderedDict()
        value["typeid"] = "malcolm:core/Table:1.0"
        value["foo"] = ("foo1", "foo2")
        value["bar"] = ("bar1", "bar2")
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "epics:nt/NTTable:1.0"
        self.serialized["labels"] = ["Foo", "bar"]
        self.serialized["meta"] = meta
        self.serialized["value"] = value
        self.serialized["alarm"] = Alarm().to_dict()
        self.serialized["timeStamp"] = TimeStamp().to_dict()

    def test_to_dict(self):
        elements = OrderedDict()
        elements["foo"] = StringArrayMeta(label="Foo")
        elements["bar"] = StringArrayMeta()
        meta = TableMeta(description="desc", tags=[], writeable=True,
                         label="my label", elements=elements)
        value = Table(meta)
        value.foo = ["foo1", "foo2"]
        value.bar = ["bar1", "bar2"]
        o = meta.create_attribute_model(value)
        o.set_timeStamp(self.serialized["timeStamp"])
        assert o.to_dict() == self.serialized

    def test_from_dict(self):
        o = NTTable.from_dict(self.serialized)
        assert list(o.meta.elements) == ["foo", "bar"]
        assert o.meta.elements["foo"].label == "Foo"
        assert o.meta.elements["bar"].label == ""
        assert o.meta.description == "desc"
        assert o.meta.tags == ()
        assert o.meta.writeable == True
        assert o.meta.label == "my label"
        assert o.value.foo == ("foo1", "foo2")
        assert o.value.bar == ("bar1", "bar2")
