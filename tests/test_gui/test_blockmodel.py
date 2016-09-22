#!/bin/env dls-python
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest

from mock import MagicMock

# module imports
from malcolm.gui.blockmodel import BlockModel, BlockItem
from malcolm.controllers.defaultcontroller import DefaultController
from malcolm.parts.demo import HelloPart


class TestBlockModel(unittest.TestCase):
    def setUp(self):
        self.process = MagicMock()
        part = HelloPart(self.process, None)
        self.block = DefaultController(
            "hello", self.process, parts={"hello":part}).block
        self.block.name = "hello"
        self.m = BlockModel(self.process, self.block)

    def test_init(self):
        self.assertEqual(self.process.q.put.call_count, 2)
        req = self.process.q.put.call_args_list[0][0][0]
        self.assertEqual(req.endpoint, ['hello', 'reset'])
        req = self.process.q.put.call_args_list[1][0][0]
        self.assertEqual(req.endpoint, ['hello'])
        self.assertEqual(self.m.root_item.endpoint, ('hello',))
        self.assertEqual(len(self.m.root_item.children), 0)

    def test_find_item(self):
        m1, m2 = MagicMock(), MagicMock()
        BlockItem.items[("foo", "bar")] = m1
        BlockItem.items[("foo",)] = m2
        item, path = self.m.find_item(('foo', 'bar', 'bat'))
        self.assertEqual(item, m1)
        self.assertEqual(path, ['bat'])

    def test_update_root(self):
        d = self.block.to_dict()
        self.m.handle_changes([[[], d]])
        b_item = self.m.root_item
        self.assertEqual(len(b_item.children), 6)
        m_item = b_item.children[5]
        self.assertEqual(m_item.endpoint, ('hello', 'say_hello'))
        self.assertEqual(len(m_item.children), 2)
        n_item = m_item.children[0]
        self.assertEqual(n_item.endpoint,
                         ('hello', 'say_hello', 'takes', 'elements', 'name'))
        self.assertEqual(n_item.children, [])
        n_item = m_item.children[1]
        self.assertEqual(n_item.endpoint,
                         ('hello', 'say_hello', 'takes', 'elements', 'sleep'))
        self.assertEqual(n_item.children, [])

if __name__ == "__main__":
    unittest.main(verbosity=2)

