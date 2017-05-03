from collections import OrderedDict
import unittest

from malcolm.core.serializable import Serializable
from malcolm.core.vmeta import VMeta


class TestVMeta(unittest.TestCase):

    def setUp(self):
        self.meta = VMeta("test description")

    def test_values_after_init(self):
        assert "test description" == self.meta.description
        assert not self.meta.writeable

    def test_given_validate_called_then_raise_error(self):
        with self.assertRaises(NotImplementedError):
            self.meta.validate(1)


class TestSerialization(unittest.TestCase):

    def setUp(self):
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "filled_in_by_subclass"
        self.serialized["description"] = "desc"
        self.serialized["tags"] = ()
        self.serialized["writeable"] = True
        self.serialized["label"] = "my label"

    def test_to_dict(self):
        m = VMeta("desc", writeable=True, label="my label")
        m.typeid = "filled_in_by_subclass"
        assert m.to_dict() == self.serialized

    def test_from_dict(self):
        @Serializable.register_subclass("filled_in_by_subclass")
        class MyVMeta(VMeta):
            pass
        m = MyVMeta.from_dict(self.serialized)
        assert m.description == "desc"
        assert m.tags == ()
        assert m.writeable == True
        assert m.label == "my label"
