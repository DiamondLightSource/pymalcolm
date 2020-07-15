import unittest

from malcolm.core import Controller, Part, PartRegistrar, Process, StringMeta


class BadPart(Part):
    def setup(self, registrar: PartRegistrar) -> None:
        attr = StringMeta().create_attribute_model()
        registrar.add_attribute_model("bad_name", attr)


class TestPart(unittest.TestCase):
    def setUp(self):
        self.c = Controller("c")
        self.p = Process("proc")

    def test_init(self):
        p = Part("name")
        assert p.name == "name"
        self.c.add_part(p)
        self.c.setup(self.p)
        assert p.registrar

    def test_bad_name(self):
        with self.assertRaises(AssertionError):
            Part("dotted.name")

    def test_good_name(self):
        Part("Part-With-dashes_43")

    def test_bad_field_name(self):
        p = BadPart("name")
        with self.assertRaises(AssertionError):
            self.c.add_part(p)
