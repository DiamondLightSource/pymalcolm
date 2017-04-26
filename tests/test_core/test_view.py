import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

import unittest
from mock import Mock

# module imports
from malcolm.core.view import make_view, View
from malcolm.core.blockmeta import BlockMeta


class TestView(unittest.TestCase):
    def setUp(self):
        self.data = BlockMeta()
        self.data.set_notifier_path(Mock(), ["block", "meta"])
        self.controller = Mock()
        self.context = Mock()
        self.o = make_view(self.controller, self.context, self.data)

    def test_init(self):
        self.assertTrue(hasattr(self.o, "description"))
        self.assertTrue(hasattr(self.o, "subscribe_description"))
        self.assertTrue(hasattr(self.o, "tags"))
        self.assertTrue(hasattr(self.o, "subscribe_tags"))
        self.assertTrue(hasattr(self.o, "writeable"))
        self.assertTrue(hasattr(self.o, "subscribe_writeable"))
        self.assertTrue(hasattr(self.o, "label"))
        self.assertTrue(hasattr(self.o, "subscribe_label"))

    def test_get_view(self):
        v = self.o.description
        self.controller.make_view.assert_called_once_with(
            self.context, self.data, "description")
        self.assertEqual(v, self.controller.make_view.return_value)

    def test_second_subclass(self):
        data2 = {"a": 2}
        o2 = make_view(self.controller, self.context, data2)
        self.assertTrue(hasattr(o2, "a"))
        self.assertTrue(hasattr(o2, "subscribe_a"))
        self.assertFalse(hasattr(self.o, "a"))
        self.assertFalse(hasattr(self.o, "subscribe_a"))

    def test_subscribe_view(self):
        cb = Mock()
        f = self.o.subscribe_label(cb)
        self.context.subscribe.assert_called_once_with(
            ["block", "meta", "label"], cb)
        self.assertEqual(f, self.context.subscribe.return_value)

    def test_view_init_fails(self):
        with self.assertRaises(NotImplementedError):
            v = View()

if __name__ == "__main__":
    unittest.main(verbosity=2)
