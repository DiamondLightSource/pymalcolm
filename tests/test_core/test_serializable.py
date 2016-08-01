import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict
import unittest
from mock import Mock

from malcolm.core.serializable import Serializable


class TestSerialization(unittest.TestCase):

    def test_to_dict(self):

        @Serializable.register_subclass("foo:1.0")
        class DummySerializable(Serializable):
            endpoints = ["boo"]
            boo = 3

            def set_boo(self, boo):
                self.boo = boo

        s = DummySerializable()
        expected = OrderedDict(typeid="foo:1.0")
        expected["boo"] = 3
        self.assertEquals(expected, s.to_dict())

        n = Serializable.from_dict(expected.copy())
        self.assertEqual(n.to_dict(), expected)



if __name__ == "__main__":
    unittest.main(verbosity=2)
