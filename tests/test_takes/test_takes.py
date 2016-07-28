import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict

import unittest
from mock import Mock, patch, call, MagicMock

from malcolm.takes.takes import Takes


class TestSetters(unittest.TestCase):

    def test_set_name(self):
        t = Takes()
        self.assertEqual(t.name, "")
        t.set_name("foo")
        self.assertEqual(t.name, "foo")

    def test_set_description(self):
        t = Takes()
        self.assertEqual(t.description, "")
        t.set_description("bar")
        self.assertEqual(t.description, "bar")

    def test_set_default_raises(self):
        t = Takes()
        self.assertRaises(NotImplementedError, t.set_default, "bat")

    def test_make_meta_raises(self):
        t = Takes()
        self.assertRaises(NotImplementedError, t.make_meta)

    def test_endpoints(self):
        t = Takes()
        self.assertEqual(t.endpoints, ["name", "description"])
        t.default = "something"
        self.assertEqual(t.endpoints, ["name", "description", "default"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
