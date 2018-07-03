import unittest
from collections import OrderedDict

import numpy
from annotypes import Anno, Array

from malcolm.core import Table

with Anno("Row A"):
    AA = Array[str]
with Anno("Row B"):
    AB = Array[int]


class MyTable(Table):
    def __init__(self, a, b):
        # type: (AA, AB) -> None
        self.a = a
        self.b = b


class TestTable(unittest.TestCase):
    def setUp(self):
        self.t = MyTable(AA(["x", "y", "z"]), AB([1, 2, 3]))
        self.serialized = OrderedDict()
        self.serialized["typeid"] = 'malcolm:core/Table:1.0'
        self.serialized["a"] = AA(["x", "y", "z"])
        self.serialized["b"] = AB([1, 2, 3])

    def test_init(self):
        t = Table()
        assert not t.call_types

    def test_from_rows(self):
        x = MyTable.from_rows([
            ["x", 1],
            ["y", 2],
            ["z", 3]
        ])
        assert x.to_dict() == self.serialized

    def test_rows(self):
        assert list(self.t.rows()) == [
            ["x", 1],
            ["y", 2],
            ["z", 3]
        ]

    def test_getitem(self):
        assert self.t[1] == ["y", 2]

    def test_roundtrip(self):
        assert MyTable.from_dict(self.serialized).to_dict() == self.serialized

    def test_equal(self):
        numpy.testing.assert_equal(self.t.to_dict(), self.t.to_dict())

    def test_not_equal(self):
        t2 = MyTable(AA(["x", "y", "z"]), AB(numpy.arange(3) + 1)).to_dict()
        numpy.testing.assert_equal(self.t.to_dict(), t2)
