import os
import sys
from collections import OrderedDict

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import call, Mock

from malcolm.core import Table
from malcolm.core.vmetas import TableMeta, BooleanArrayMeta, NumberArrayMeta
from malcolm.parts.pandabox.pandaboxtablepart import PandABoxTablePart


class PandABoxTablePartTest(unittest.TestCase):
    def setUp(self):
        self.process = Mock()
        self.control = Mock()
        fields = OrderedDict()
        fields["NREPEATS"] = (7, 0)
        fields["INPUT_MASK"] = (32, 32)
        fields["TRIGGER_MASK"] = (48, 48)
        fields["TIME_PH_A"] = (95, 64)
        self.control.get_table_fields.return_value = fields
        self.meta = TableMeta("Seq table")
        self.o = PandABoxTablePart(
            self.process, self.control, self.meta,
            block_name="SEQ1", field_name="TABLE", writeable=True)

    def test_init(self):
        self.assertEqual(list(self.meta.elements), [
            "nrepeats", "inputMask", "triggerMask", "timePhA"])
        self.assertIsInstance(self.meta.elements.nrepeats, NumberArrayMeta)
        self.assertEqual(self.meta.elements.nrepeats.dtype, "uint8")
        self.assertEqual(self.meta.elements.nrepeats.tags, ("widget:textinput",))
        self.assertIsInstance(self.meta.elements.inputMask, BooleanArrayMeta)
        self.assertEqual(self.meta.elements.inputMask.tags, ("widget:checkbox",))
        self.assertIsInstance(self.meta.elements.triggerMask, BooleanArrayMeta)
        self.assertEqual(self.meta.elements.triggerMask.tags, ("widget:checkbox",))
        self.assertIsInstance(self.meta.elements.timePhA, NumberArrayMeta)
        self.assertEqual(self.meta.elements.timePhA.dtype, "uint32")
        self.assertEqual(self.meta.elements.timePhA.tags, ("widget:textinput",))

    def test_list_from_table(self):
        table = Table(self.meta)
        table.append([32, True, True, 4294967295])
        table.append([0, True, False, 1])
        table.append([0, False, False, 0])
        l = self.o.list_from_table(table)
        self.assertEqual(l,
                         [32, 0x10001, 4294967295,
                         0, 0x1, 1,
                         0, 0x0, 0])

    def test_table_from_list(self):
        l = [32, 0x10001, 4294967295,
             0, 0x1, 1,
             0, 0x0, 0]
        table = self.o.table_from_list(l)
        self.assertEqual(list(table.nrepeats), [32, 0, 0])
        self.assertEqual(list(table.inputMask), [True, True, False])
        self.assertEqual(list(table.triggerMask), [True, False, False])
        self.assertEqual(list(table.timePhA), [4294967295, 1, 0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
