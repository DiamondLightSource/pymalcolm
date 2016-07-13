import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import Mock

from malcolm.core.serializable import Serializable

# Register Serializable as a sublcass of itself so we
# can instantiate it for testing purposes.
Serializable.register_subclass("serializable:test")(Serializable)


class TestSerialization(unittest.TestCase):

    def test_to_dict(self):

        @Serializable.register_subclass("foo:1.0")
        class DummySerializable(Serializable):
            from_dict = Mock()

        s = DummySerializable()
        self.assertEquals({"typeid": "foo:1.0"}, s.to_dict())

    def test_base_deserialize_calls_from_dict(self):

        @Serializable.register_subclass("foo:1.0")
        class DummySerializable(Serializable):
            from_dict = Mock()

        s = DummySerializable()
        d = dict(typeid="foo:1.0", value=0)

        Serializable.deserialize("name", d)

        s.from_dict.assert_called_once_with("name", d)

    def test_from_dict_calls_update(self):

        @Serializable.register_subclass("foo:1.0")
        class DummySerializable(Serializable):
            update = Mock()

        s = DummySerializable()

        d = dict(value=0)
        DummySerializable.from_dict("name", d)

        s.update.assert_called_once_with(["value", 0])

    def test_update_calls_set(self):

        @Serializable.register_subclass("foo:1.0")
        class DummySerializable(Serializable):
            set_value = Mock()

        s = DummySerializable()

        s.update(("value", 0))

        s.set_value.assert_called_once_with(0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
