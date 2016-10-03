import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, patch

# module imports
from malcolm.gui.baseitem import BaseItem


class TestBaseItem(unittest.TestCase):

    def setUp(self):
        ref = MagicMock()
        BaseItem.items = {}
        self.item = BaseItem(("endpoint",), ref)

    def test_init(self):
        self.assertEqual(self.item.items, {("endpoint",): self.item})

    @patch("malcolm.gui.baseitem.QApplication")
    def test_get_icon(self, app_mock):
        icon = MagicMock()
        app_mock.style().standardIcon.return_value = icon
        self.assertEqual(self.item.get_icon(), icon)
        app_mock.style().standardIcon.assert_called_once_with(
            BaseItem.icons[BaseItem.IDLE])

    def test_get_label_from_meta(self):
        self.item.endpoint = ("foo", "bar")
        self.item.ref.meta.label = "Bar"
        self.assertEqual(self.item.get_label(), "Bar")

    def test_get_label_from_meta(self):
        self.item.endpoint = ("foo", "bar")
        del self.item.ref.meta
        self.assertEqual(self.item.get_label(), "bar")

    def test_get_value(self):
        self.assertEqual(self.item.get_value(), None)

    def test_get_writeable(self):
        self.assertEqual(self.item.get_writeable(), False)

    def test_get_state(self):
        self.assertEqual(self.item.get_state(), BaseItem.IDLE)

    def test_add_remove_child(self):
        child1 = BaseItem(("c1",), None)
        child2 = BaseItem(("c2",), None)
        self.item.add_child(child1)
        self.assertEqual(child1.parent_row(), 0)
        self.assertEqual(child1.parent_item, self.item)
        self.assertEqual(self.item.children, [child1])
        self.item.add_child(child2)
        self.assertEqual(child2.parent_row(), 1)
        self.assertEqual(self.item.children, [child1, child2])
        self.assertEqual(BaseItem.items, {
            ("endpoint",): self.item,
            ("c1",): child1,
            ("c2",): child2})
        self.item.remove_child(child1)
        self.assertEqual(self.item.children, [child2])
        self.assertEqual(BaseItem.items, {
            ("endpoint",): self.item,
            ("c2",): child2})

    def test_ref_children(self):
        self.assertEqual(self.item.ref_children(), 0)

    def test_create_children(self):
        self.assertEqual(self.item.create_children(), None)

    def test_set_value(self):
        self.assertRaises(NotImplementedError, self.item.set_value, "anything")

if __name__ == "__main__":
    unittest.main(verbosity=2)
