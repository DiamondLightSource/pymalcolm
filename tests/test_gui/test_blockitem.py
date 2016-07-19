import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from collections import OrderedDict
from mock import MagicMock, patch

# module imports
from malcolm.gui.blockitem import BlockItem


class TestBlockItem(unittest.TestCase):

    def setUp(self):
        ref = MagicMock()
        BlockItem.items.clear()
        self.item = BlockItem(("endpoint",), ref)

    def test_ref_children(self):
        self.item.ref.methods = dict(a=1, b=2)
        self.item.ref.attributes = dict(c=MagicMock())
        self.assertEqual(self.item.ref_children(), 3)

    def make_grouped_attr(self):
        attr = MagicMock()
        attr.tags = ["group:foo"]
        return attr

    def test_group_name(self):
        attr = self.make_grouped_attr()
        self.assertEqual(self.item._get_group_name(attr), "foo")

    def test_grouped_children(self):
        attr = self.make_grouped_attr()
        self.item.ref.attributes = dict(c=attr, d=MagicMock())
        self.assertEqual(self.item.ref_children(), 1)

    @patch("malcolm.gui.blockitem.MethodItem")
    @patch("malcolm.gui.blockitem.AttributeItem")
    def test_create_children(self, attribute_mock, method_mock):
        # Load up items to create
        mi1, mi2 = MagicMock(), MagicMock()
        method_mock.side_effect = [mi1, mi2]
        ai1, ai2 = MagicMock(), MagicMock()
        attribute_mock.side_effect = [ai1, ai2]
        # Load up refs to get
        group_attr = MagicMock()
        child_attr = self.make_grouped_attr()
        BlockItem.items[("endpoint", "foo")] = ai1
        self.item.ref.methods = OrderedDict((("a", 1), ("b", 2)))
        self.item.ref.attributes = OrderedDict((("foo", group_attr), ("c", child_attr)))
        self.item.create_children()
        # Check it made the right thing
        self.assertEqual(len(self.item.children), 3)
        attribute_mock.assert_any_call(("endpoint", "foo"), group_attr)
        self.assertEqual(self.item.children[0], ai1)
        attribute_mock.assert_any_call(("endpoint", "c"), child_attr)
        ai1.add_child.assert_called_once_with(ai2)
        method_mock.assert_any_call(("endpoint", "a"), 1)
        self.assertEqual(self.item.children[1], mi1)
        method_mock.assert_any_call(("endpoint", "b"), 2)
        self.assertEqual(self.item.children[2], mi2)



if __name__ == "__main__":
    unittest.main(verbosity=2)

