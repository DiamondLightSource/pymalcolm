import os
import sys
sys.path.append(os.path.dirname(__file__))
import setup_malcolm_paths

import unittest
from mock import Mock, ANY

from malcolm.core import method_takes, REQUIRED
from malcolm.core.vmetas import StringMeta
from malcolm.parts.ca.cadoublepart import CADoublePart
from malcolm.yamlutil import make_block_creator, Section, make_include_creator


class TestAssemblies(unittest.TestCase):

    def test_all_yamls(self):
        from malcolm.blocks.demo import Hello
        process = Mock()
        blocks = Hello(process, dict(mri="boo"))
        self.assertEqual(len(blocks), 1)
        process.add_block.assert_called_once_with(blocks[0], ANY)

    def test_make_include(self):
        yaml = """
- parameters.string:
    name: something
    description: my description

- parts.ca.CADoublePart:
    name: double
    description: the pv object
    pv: $(something)
"""
        include_creator = make_include_creator(yaml)
        process = Mock()
        blocks, parts = include_creator(process, dict(something="mypv"))
        self.assertEquals(len(blocks), 0)
        self.assertEquals(len(parts), 1)
        part = parts[0]
        self.assertIsInstance(part, CADoublePart)
        self.assertEqual(part.name, "double")
        self.assertEqual(part.params.pv, "mypv")

    def test_make_block(self):
        yaml = """
- parameters.string:
    name: something
    description: my description

- controllers.DefaultController:
    mri: boo

- parts.ca.CADoublePart:
    name: double
    description: the pv object
    pv: $(something)
"""
        block_creator = make_block_creator(yaml)
        process = Mock()
        blocks = block_creator(process, dict(something="mypv"))
        self.assertEquals(len(blocks), 1)
        block, controller = process.add_block.call_args[0]
        self.assertEquals(len(controller.parts), 1)
        self.assertIsInstance(controller.parts["double"], CADoublePart)
        self.assertEqual(controller.parts["double"].params.pv, "mypv")

    def test_instantiate(self):
        @method_takes(
            "desc", StringMeta("description"), REQUIRED,
            "foo", StringMeta("optional thing"), "thing"
        )
        def f(extra, params):
            return extra, 2, params.desc, params.foo

        ca = Mock(CAPart=f)
        parts = Mock(ca=ca)
        section = Section("ca.CAPart", dict(desc="my name"))
        result = section.instantiate({}, parts, "extra")
        self.assertEqual(result, ("extra", 2, "my name", "thing"))

    def test_split_into_sections(self):
        text = """
- parameters.string:
    name: something
- controllers.ManagerController:
"""
        sections = Section.from_yaml(text)
        self.assertEqual(sections, dict(
            blocks=[],
            parameters=[ANY],
            controllers=[ANY],
            parts=[],
            includes=[],
            comms=[]))
        self.assertEqual(sections["parameters"][0].name, "string")
        self.assertEqual(sections["parameters"][0].param_dict,
                         {"name": "something"})
        self.assertEqual(sections["controllers"][0].name, "ManagerController")
        self.assertEqual(sections["controllers"][0].param_dict, {})

    def test_substitute_params(self):
        section = Section("name", {"name": "$(name):pos", "exposure": 1.0})
        params = {"name": "me"}
        param_dict = section.substitute_params(params)
        expected = {"name": "me:pos", "exposure": 1.0}
        self.assertEqual(param_dict, expected)


    def test_repr(self):
        s = Section("ca.CADoublePart", {"name": "me"})
        expected = "Section(ca.CADoublePart, {'name': 'me'})"
        self.assertEqual(repr(s), expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
