import os
import sys
sys.path.append(os.path.dirname(__file__))

import unittest
from mock import Mock, ANY, patch, mock_open

from malcolm.core import method_takes, REQUIRED
from malcolm.controllers.builtin import BaseController
from malcolm.vmetas.builtin import StringMeta
from malcolm.parts.builtin.stringpart import StringPart
from malcolm.yamlutil import make_block_creator, Section, make_include_creator

include_yaml = """
- parameters.string:
    name: something
    description: my description

- parts.builtin.StringPart:
    name: scannable
    description: Scannable name for motor
    initialValue: $(something)
"""

block_yaml = """
- parameters.string:
    name: something
    description: my description

- controllers.builtin.BaseController:
    mri: some_mri

- parts.builtin.StringPart:
    name: scannable
    description: Scannable name for motor
    initialValue: $(something)
"""


class TestYamlUtil(unittest.TestCase):

    def test_all_yamls(self):
        from malcolm.blocks.demo import hello_block
        process = Mock()
        controller = hello_block(process, dict(mri="h"))
        assert isinstance(controller, BaseController)
        process.add_controller.assert_called_once_with("h", controller)

    def test_make_include(self):
        with patch("malcolm.yamlutil.open",
                   mock_open(read_data=include_yaml), create=True) as m:
            include_creator = make_include_creator(
                "/tmp/__init__.py", "include.yaml")
        m.assert_called_once_with("/tmp/include.yaml")
        process = Mock()
        parts = include_creator(process, dict(something="blah"))
        self.assertEquals(len(parts), 1)
        part = parts[0]
        self.assertIsInstance(part, StringPart)
        self.assertEqual(part.name, "scannable")
        self.assertEqual(part.params.initialValue, "blah")

    def test_make_block(self):
        with patch("malcolm.yamlutil.open",
                   mock_open(read_data=block_yaml), create=True) as m:
            block_creator = make_block_creator(
                "/tmp/__init__.py", "block.yaml")
        m.assert_called_once_with("/tmp/block.yaml")
        process = Mock()
        controller = block_creator(process, dict(something="blah"))
        process.add_controller.assert_called_once_with("some_mri", controller)
        self.assertEquals(len(controller.parts), 1)
        self.assertIsInstance(controller.parts["scannable"], StringPart)
        self.assertEqual(controller.parts["scannable"].params.initialValue,
                         "blah")

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

- controllers.builtin.ManagerController:
    mri: m
"""
        sections = Section.from_yaml(text)
        assert sections == dict(
            blocks=[],
            parameters=[ANY],
            controllers=[ANY],
            parts=[],
            includes=[])
        assert sections["parameters"][0].name == "string"
        assert sections["parameters"][0].param_dict == dict(name="something")
        assert sections["controllers"][0].name == "builtin.ManagerController"
        assert sections["controllers"][0].param_dict == dict(mri="m")

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
