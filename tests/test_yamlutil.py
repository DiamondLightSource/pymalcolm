import os
import sys
sys.path.append(os.path.dirname(__file__))

import unittest
from mock import Mock, ANY, patch, mock_open

from malcolm.core import method_takes, REQUIRED
from malcolm.modules.builtin.controllers import BaseController
from malcolm.modules.builtin.vmetas import StringMeta
from malcolm.modules.builtin.parts import StringPart
from malcolm.yamlutil import make_block_creator, Section, check_yaml_names, \
    make_include_creator

include_yaml = """
- builtin.parameters.string:
    name: something
    description: my description

- builtin.parts.StringPart:
    name: scannable
    description: Scannable name for motor
    initialValue: $(something)
"""

block_yaml = """
- builtin.parameters.string:
    name: something
    description: my description

- builtin.controllers.BaseController:
    mri: some_mri

- builtin.parts.StringPart:
    name: scannable
    description: Scannable name for motor
    initialValue: $(something)
"""


class TestYamlUtil(unittest.TestCase):

    def test_all_yamls(self):
        from malcolm.modules.demo.blocks import hello_block
        process = Mock()
        controller = hello_block(process, dict(mri="h"))
        assert isinstance(controller, BaseController)
        process.add_controller.assert_called_once_with("h", controller)

    def test_make_include(self):
        with patch("malcolm.yamlutil.open",
                   mock_open(read_data=include_yaml), create=True) as m:
            include_creator = make_include_creator(
                "/tmp/__init__.py", "include.yaml")
        assert include_creator.yamlname == "include"
        m.assert_called_once_with("/tmp/include.yaml")
        process = Mock()
        parts = include_creator(process, dict(something="blah"))
        assert len(parts) == 1
        part = parts[0]
        self.assertIsInstance(part, StringPart)
        assert part.name == "scannable"
        assert part.params.initialValue == "blah"

    def test_make_block(self):
        with patch("malcolm.yamlutil.open",
                   mock_open(read_data=block_yaml), create=True) as m:
            block_creator = make_block_creator(
                "/tmp/__init__.py", "block.yaml")
        assert block_creator.yamlname == "block"
        m.assert_called_once_with("/tmp/block.yaml")
        process = Mock()
        controller = block_creator(process, dict(something="blah"))
        process.add_controller.assert_called_once_with("some_mri", controller)
        assert len(controller.parts) == 1
        self.assertIsInstance(controller.parts["scannable"], StringPart)
        assert controller.parts["scannable"].params.initialValue == (
                         "blah")

    def test_check_names_good(self):
        d = dict(
            thinga=Mock(yamlname="thinga"),
            thingb=Mock(yamlname="thingb"))
        d_save = d.copy()
        check_yaml_names(d_save)
        assert d == d_save

    def test_check_names_mismatch(self):
        d = dict(
            thinga=Mock(yamlname="thinga"),
            thingb=Mock(yamlname="thingc"))
        d_save = d.copy()
        with self.assertRaises(AssertionError) as cm:
            check_yaml_names(d_save)
        assert str(cm.exception) == \
            "'thingb' should be called 'thingc' as it comes from 'thingc.yaml'"

    @patch("importlib.import_module")
    def test_instantiate(self, mock_import):
        @method_takes(
            "desc", StringMeta("description"), REQUIRED,
            "foo", StringMeta("optional thing"), "thing"
        )
        def f(extra, params):
            return extra, 2, params.desc, params.foo

        mock_import.return_value = Mock(MyPart=f)

        section = Section("f", 1, "mymodule.parts.MyPart", dict(desc="my name"))
        result = section.instantiate({}, "extra")
        mock_import.assert_called_once_with("malcolm.modules.mymodule.parts")
        assert result == ("extra", 2, "my name", "thing")

    def test_split_into_sections(self):
        filename = "/tmp/yamltest.yaml"
        with open(filename, "w") as f:
            f.write("""
- builtin.parameters.string:
    name: something

- builtin.controllers.ManagerController:
    mri: m
""")
        sections = Section.from_yaml(filename)
        assert sections == (dict(
            blocks=[],
            parameters=[ANY],
            controllers=[ANY],
            parts=[],
            includes=[]), "yamltest")
        assert sections[0]["parameters"][0].name == "builtin.parameters.string"
        assert sections[0]["parameters"][0].param_dict == dict(name="something")
        assert sections[0]["controllers"][0].name == "builtin.controllers.ManagerController"
        assert sections[0]["controllers"][0].param_dict == dict(mri="m")

    def test_substitute_params(self):
        section = Section(
            "f", 1, "name", {"name": "$(name):pos", "exposure": 1.0})
        params = {"name": "me"}
        param_dict = section.substitute_params(params)
        expected = {"name": "me:pos", "exposure": 1.0}
        assert param_dict == expected

    def test_repr(self):
        s = Section("f", 1, "ca.CADoublePart", {"name": "me"})
        expected = "Section(ca.CADoublePart, {'name': 'me'})"
        assert repr(s) == expected


if __name__ == "__main__":
    unittest.main(verbosity=2)
