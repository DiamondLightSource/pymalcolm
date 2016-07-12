import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import Mock

from malcolm.core.serializable import Serializable

# Register Serializable as a sublcass of itself so we
# can instantiate it for testing purposes.
Serializable.register("serializable:test")(Serializable)

class TestSerialization(unittest.TestCase):

    def test_to_dict(self):
        @Serializable.register("foo:1.0")
        class DummySerializable(Serializable):
            from_dict = Mock()
        s = DummySerializable("name")
        self.assertEquals({"typeid":"foo:1.0"}, s.to_dict())

    def test_from_dict_returns(self):
        @Serializable.register("foo:1.0")
        class DummySerializable(Serializable):
            from_dict = Mock()
        s = DummySerializable("name")

        d = dict(typeid = "foo:1.0")
        deserialized = Serializable.from_dict("me", d)

        s.from_dict.assert_called_once_with("me", d)
        self.assertEqual(s.from_dict.return_value, deserialized)

    def test_from_dict_not_defined_on_subclass_fails(self):
        @Serializable.register("anything")
        class Faulty(Serializable):
            pass
        self.assertRaises(AssertionError, Serializable.from_dict,
                          "me", dict(typeid="anything"))

if __name__ == "__main__":
    unittest.main(verbosity=2)
