import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict

import unittest

from malcolm.takes import StringTakes
from malcolm.metas import StringMeta
from malcolm.core.method import REQUIRED


class TestSetters(unittest.TestCase):

    def test_set_default(self):
        t = StringTakes()
        t.set_default("foo")
        self.assertEqual(t.default, "foo")

    def test_make_meta(self):
        t = StringTakes()
        t.set_name("me")
        t.set_description("desc")
        meta = t.make_meta()
        self.assertEqual(meta.name, "me")
        self.assertEqual(meta.description, "desc")
        self.assertIsInstance(meta, StringMeta)


class TestSerialization(unittest.TestCase):

    def setUp(self):
        self.s = OrderedDict(typeid="takes.StringTakes")
        self.s["name"] = "param"
        self.s["description"] = "description"

    def test_from_dict(self):
        t = StringTakes.from_dict("param", self.s)
        self.assertIsInstance(t, StringTakes)
        self.assertEqual(t.name, "param")
        self.assertEqual(t.description, "description")
        self.assertEqual(t.default, REQUIRED)
        self.s["default"] = "something"
        t = StringTakes.from_dict("param", self.s)
        self.assertEqual(t.default, "something")

    def test_do_dict(self):
        t = StringTakes()
        t.set_name("param")
        t.set_description("description")
        self.assertEqual(t.to_dict(), self.s)

if __name__ == "__main__":
    unittest.main(verbosity=2)
