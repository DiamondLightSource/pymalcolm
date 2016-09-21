import os
import sys
sys.path.append(os.path.dirname(__file__))
import setup_malcolm_paths

import unittest
from mock import Mock, patch, ANY

from malcolm.core import method_takes, REQUIRED, Block
from malcolm.core.vmetas import StringMeta
from malcolm.assemblyutil import make_assembly, Section, make_block_instance


class TestAssemblies(unittest.TestCase):

    def test_all_yamls(self):
        from malcolm.assemblies.demo import Hello
        process = Mock()
        blocks = Hello(process, dict(name="boo"))
        self.assertEqual(len(blocks), 1)
        process.add_block.assert_called_once_with(blocks[0])

    @patch("malcolm.assemblyutil.make_block_instance")
    def test_make_assembly(self, mock_make):
        yaml = """
- parameters.string:
    name: something
    description: my description

- parts.ca.CADoublePart:
    pv: $(something)
"""
        collection = make_assembly(yaml)
        process = Mock()
        blocks = collection(process, dict(name="boo", something="mypv"))
        mock_make.assert_called_once_with(
            "boo", process, [], [ANY])
        section = mock_make.call_args[0][3][0]
        self.assertEqual(section.name, "ca.CADoublePart")
        self.assertEqual(section.param_dict, {"pv": "mypv"})
        self.assertEqual(blocks, [mock_make.return_value])

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
        result = section.instantiate(parts, "extra")
        self.assertEqual(result, ("extra", 2, "my name", "thing"))

    def test_split_into_sections(self):
        ds = [{"parameters.string": {"name": "something"}},
              {"controllers.ManagerController": None}]
        sections = Section.split_into_sections(ds)
        self.assertEqual(sections, dict(
            parameters=[ANY],
            controllers=[ANY],
            parts=[],
            assemblies=[],
            comms=[]))
        self.assertEqual(sections["parameters"][0].name, "string")
        self.assertEqual(sections["parameters"][0].param_dict,
                         {"name": "something"})
        self.assertEqual(sections["controllers"][0].name, "ManagerController")
        self.assertEqual(sections["controllers"][0].param_dict, {})

    def test_substitute_params(self):
        section = Section("name", {"name": "$(name):pos", "exposure": 1.0})
        params = {"name": "me"}
        section.substitute_params(params)
        expected = {"name": "me:pos", "exposure": 1.0}
        self.assertEqual(section.param_dict, expected)

    def test_make_block_instance(self):
        parts = [Section("ca.CADoublePart", {
            "name": "me", "description": "my pv desc", "pv": "MY:PV:STRING"})]
        controllers = []
        block_name = "block_name"
        process = Mock()
        inst = make_block_instance(block_name, process, controllers, parts)
        self.assertIsInstance(inst, Block)
        process.add_block.assert_called_once_with(inst)
        self.assertEqual(inst.path_relative_to(process), [block_name])
        self.assertEqual(
            list(inst),
            ['meta', 'state', 'status', 'busy', 'disable', 'reset', 'me'])

    def test_make_block_instance_custom_controller(self):
        parts = []
        controllers = [Section("ManagerController")]
        block_name = "block_name"
        process = Mock()
        inst = make_block_instance(block_name, process, controllers, parts)
        self.assertIsInstance(inst, Block)
        process.add_block.assert_called_once_with(inst)

    def test_repr(self):
        s = Section("ca.CADoublePart", {"name": "me"})
        expected = "Section(ca.CADoublePart, {'name': 'me'})"
        self.assertEqual(repr(s), expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
