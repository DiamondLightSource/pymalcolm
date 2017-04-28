import unittest
from mock import MagicMock, patch

from malcolm.gui.baseitem import BaseItem


class TestBaseItem(unittest.TestCase):

    def setUp(self):
        ref = MagicMock()
        BaseItem.items = {}
        self.item = BaseItem(("endpoint",), ref)

    def test_init(self):
        assert self.item.items == {("endpoint",): self.item}

    @patch("malcolm.gui.baseitem.QApplication")
    def test_get_icon(self, app_mock):
        icon = MagicMock()
        app_mock.style().standardIcon.return_value = icon
        assert self.item.get_icon() == icon
        app_mock.style().standardIcon.assert_called_once_with(
            BaseItem.icons[BaseItem.IDLE])

    def test_get_label_from_meta(self):
        self.item.endpoint = ("foo", "bar")
        self.item.ref.meta.label = "Bar"
        assert self.item.get_label() == "Bar"

    def test_get_label_from_meta(self):
        self.item.endpoint = ("foo", "bar")
        del self.item.ref.meta
        assert self.item.get_label() == "bar"

    def test_get_value(self):
        assert self.item.get_value() == None

    def test_get_writeable(self):
        assert self.item.get_writeable() == False

    def test_get_state(self):
        assert self.item.get_state() == BaseItem.IDLE

    def test_add_remove_child(self):
        child1 = BaseItem(("c1",), None)
        child2 = BaseItem(("c2",), None)
        self.item.add_child(child1)
        assert child1.parent_row() == 0
        assert child1.parent_item == self.item
        assert self.item.children == [child1]
        self.item.add_child(child2)
        assert child2.parent_row() == 1
        assert self.item.children == [child1, child2]
        assert BaseItem.items == {
            ("endpoint",): self.item,
            ("c1",): child1,
            ("c2",): child2}
        self.item.remove_child(child1)
        assert self.item.children == [child2]
        assert BaseItem.items == {
            ("endpoint",): self.item,
            ("c2",): child2}

    def test_ref_children(self):
        assert self.item.ref_children() == 0

    def test_create_children(self):
        assert self.item.create_children() == None

    def test_set_value(self):
        with self.assertRaises(NotImplementedError):
            self.item.set_value("anything")
