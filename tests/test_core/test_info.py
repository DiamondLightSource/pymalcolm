import unittest

from malcolm.compat import OrderedDict
from malcolm.core import Info


class MyInfo(Info):
    def __init__(self, val):
        self.val = val


class TestInit(unittest.TestCase):
    def setUp(self):
        self.d1 = dict(parta=[], partb=None)
        self.d2 = OrderedDict()
        self.d2["parta"] = []
        self.d2["partb"] = [MyInfo("v1")]
        self.d2["partc"] = [MyInfo("v2"), MyInfo("v3")]
        self.d2["partd"] = None

    def test_repr(self):
        assert repr(MyInfo("thing")) == "MyInfo('thing')"

    def test_filter_parts(self):
        filtered = MyInfo.filter_parts(self.d1)
        assert len(filtered) == 0
        filtered = MyInfo.filter_parts(self.d2)
        assert len(filtered) == 2
        assert len(filtered["partb"]) == 1
        assert filtered["partb"][0].val == "v1"
        assert len(filtered["partc"]) == 2
        assert filtered["partc"][0].val == "v2"
        assert filtered["partc"][1].val == "v3"

    def test_filer_values(self):
        filtered = MyInfo.filter_values(self.d1)
        assert len(filtered) == 0
        filtered = MyInfo.filter_values(self.d2)
        assert len(filtered) == 3
        assert filtered[0].val == "v1"
        assert filtered[1].val == "v2"
        assert filtered[2].val == "v3"
