import unittest

from malcolm.core import StringArray


class TestStringArray(unittest.TestCase):
    def test_strings_instance(self):
        a = StringArray("boo", "bar")
        self.assertIsInstance(a, tuple)
        self.assertIsInstance(a, StringArray)
        assert a == ("boo", "bar")

    def test_immutable(self):
        a = StringArray("boo", "bar")
        with self.assertRaises(TypeError):
            a[0] = "bat"

    def test_single_element(self):
        a = StringArray("boo")
        assert a == ("boo",)

    def test_iterable(self):
        a = StringArray("a%s" % i for i in range(3))
        assert a == ("a0", "a1", "a2")

    def test_tuple(self):
        a = StringArray(("boo", "bar"))
        assert a == ("boo", "bar")

    def test_non_strings_raise(self):
        with self.assertRaises(ValueError) as cm:
            StringArray(1, 2, 3)
        assert (
            str(cm.exception)) == (
            'Expected StringArray(s1, s2, ...) or StringArray(seq). '
            'Got StringArray(1, 2, 3)')
