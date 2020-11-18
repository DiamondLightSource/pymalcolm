import os
import sys
import unittest

from annotypes import Anno, Any, add_call_types
from mock import ANY, Mock, mock_open, patch

from malcolm.modules.builtin.controllers import BasicController
from malcolm.modules.builtin.parts import StringPart
from malcolm.yamlutil import (
    Section,
    check_yaml_names,
    make_block_creator,
    make_include_creator,
)

sys.path.append(os.path.dirname(__file__))


include_yaml = """
- builtin.parameters.string:
    name: something
    description: my description
    default: nothing

- builtin.parts.StringPart:
    name: scannable
    description: Scannable name for motor
    value: $(something)
"""

block_yaml = """
- builtin.parameters.string:
    name: something
    description: my description

- builtin.controllers.BasicController:
    mri: some_mri

- builtin.parts.StringPart:
    name: scannable
    description: Scannable name for motor
    value: $(something)
"""

with Anno("Description"):
    ADesc = str
with Anno("Thing"):
    AThing = str


class TestYamlUtil(unittest.TestCase):
    def test_existing_yaml(self):
        from malcolm.modules.demo.blocks import hello_block

        controllers = hello_block(mri="h")
        assert len(controllers) == 1
        assert isinstance(controllers[0], BasicController)
        assert len(controllers[0].parts) == 1

    def test_make_include(self):
        with patch(
            "malcolm.yamlutil.open", mock_open(read_data=include_yaml), create=True
        ) as m:
            include_creator = make_include_creator("/tmp/__init__.py", "include.yaml")
        assert include_creator.__name__ == "include"
        m.assert_called_once_with("/tmp/include.yaml")
        controllers, parts = include_creator()
        assert len(controllers) == 0
        assert len(parts) == 1
        part = parts[0]
        self.assertIsInstance(part, StringPart)
        assert part.name == "scannable"
        assert part.attr.value == "nothing"

    def test_make_block(self):
        with patch(
            "malcolm.yamlutil.open", mock_open(read_data=block_yaml), create=True
        ) as m:
            block_creator = make_block_creator("/tmp/__init__.py", "block.yaml")
        assert block_creator.__name__ == "block"
        m.assert_called_once_with("/tmp/block.yaml")
        controllers = block_creator(something="blah")
        assert len(controllers) == 1
        parts = controllers[0].parts
        assert len(parts) == 1
        self.assertIsInstance(parts["scannable"], StringPart)
        assert parts["scannable"].attr.value == "blah"

    def test_check_names_good(self):
        d = dict(
            thinga=Mock(yamlname="thinga"),
            thingb=Mock(yamlname="thingb"),
            hidden=Mock(spec=dict),
        )
        a = check_yaml_names(d)
        assert a == ["thinga", "thingb"]

    def test_check_names_mismatch(self):
        d = dict(thinga=Mock(yamlname="thinga"), thingb=Mock(yamlname="thingc"))
        with self.assertRaises(AssertionError) as cm:
            check_yaml_names(d)
        assert (
            str(cm.exception)
            == "'thingb' should be called 'thingc' as it comes from 'thingc.yaml'"
        )

    @patch("importlib.import_module")
    def test_instantiate(self, mock_import):
        @add_call_types
        def f(desc: ADesc, foo: AThing = "thing") -> Any:
            return 2, desc, foo

        mock_import.return_value = Mock(MyPart=f)

        section = Section("f", 1, "mymodule.parts.MyPart", dict(desc="my name"))
        result = section.instantiate({})
        mock_import.assert_called_once_with("malcolm.modules.mymodule.parts")
        assert result == (2, "my name", "thing")

    def test_split_into_sections(self):
        filename = "/tmp/yamltest.yaml"
        with open(filename, "w") as f:
            f.write(
                """
- builtin.parameters.string:
    name: something

- builtin.controllers.ManagerController:
    mri: m

- builtin.defines.docstring:
    value: My special docstring
"""
            )
        sections = Section.from_yaml(filename)
        assert sections == ([ANY, ANY, ANY], "yamltest", "My special docstring")
        assert sections[0][0].name == "builtin.parameters.string"
        assert sections[0][0].param_dict == dict(name="something")
        assert sections[0][1].name == "builtin.controllers.ManagerController"
        assert sections[0][1].param_dict == dict(mri="m")
        assert sections[0][2].name == "builtin.defines.docstring"
        assert sections[0][2].param_dict == dict(value="My special docstring")

    def test_substitute_params(self):
        section = Section(
            "f", 1, "module.parts.name", {"name": "$(name):pos", "exposure": 1.0}
        )
        params = {"name": "me"}
        param_dict = section.substitute_params(params)
        expected = {"name": "me:pos", "exposure": 1.0}
        assert param_dict == expected

    def test_repr(self):
        s = Section("f", 1, "ca.parts.CADoublePart", {"name": "me"})
        expected = "Section(ca.parts.CADoublePart, {'name': 'me'})"
        assert repr(s) == expected


if __name__ == "__main__":
    unittest.main(verbosity=2)
