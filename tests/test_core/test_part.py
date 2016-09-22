import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest

from mock import Mock

from malcolm.controllers.defaultcontroller import DefaultController
from malcolm.core import Part, method_takes


class MyPart(Part):
    @method_takes()
    @DefaultController.Resetting
    def foo(self):
        pass

    @method_takes()
    def bar(self):
        pass


class TestPart(unittest.TestCase):
    def test_init(self):
        process = Mock()
        params = Mock()
        p = Part(process, params)
        self.assertEqual(p.params, params)
        self.assertEqual(p.process, process)

    def test_non_hooked_methods(self):
        p = MyPart(Mock(), Mock())
        methods = list(p.create_methods())
        self.assertEqual(methods, [("bar", p.bar.MethodMeta, p.bar)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
