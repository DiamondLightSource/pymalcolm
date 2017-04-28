import unittest
from mock import Mock

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
        assert hasattr(self.o, "description")
        assert hasattr(self.o, "subscribe_description")
        assert hasattr(self.o, "tags")
        assert hasattr(self.o, "subscribe_tags")
        assert hasattr(self.o, "writeable")
        assert hasattr(self.o, "subscribe_writeable")
        assert hasattr(self.o, "label")
        assert hasattr(self.o, "subscribe_label")

    def test_get_view(self):
        v = self.o.description
        self.controller.make_view.assert_called_once_with(
            self.context, self.data, "description")
        assert v == self.controller.make_view.return_value

    def test_second_subclass(self):
        data2 = {"a": 2}
        o2 = make_view(self.controller, self.context, data2)
        assert hasattr(o2, "a")
        assert hasattr(o2, "subscribe_a")
        assert not hasattr(self.o, "a")
        assert not hasattr(self.o, "subscribe_a")

    def test_subscribe_view(self):
        cb = Mock()
        f = self.o.subscribe_label(cb)
        self.context.subscribe.assert_called_once_with(
            ["block", "meta", "label"], cb)
        assert f == self.context.subscribe.return_value

    def test_view_init_fails(self):
        with self.assertRaises(NotImplementedError):
            v = View()
