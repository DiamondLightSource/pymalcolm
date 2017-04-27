import unittest

from malcolm.core import Part, method_takes, Hook


Reset = Hook()


class MyPart(Part):
    @method_takes()
    @Reset
    def foo(self):
        pass

    @method_takes()
    def bar(self):
        pass


class TestPart(unittest.TestCase):
    def test_init(self):
        p = Part("name")
        self.assertEqual(p.name, "name")

    def test_non_hooked_methods(self):
        p = MyPart("")
        methods = list(p.create_methods())
        self.assertEqual(methods, [("bar", p.method_models["bar"], p.bar)])
