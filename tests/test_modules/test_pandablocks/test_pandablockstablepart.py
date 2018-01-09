from collections import OrderedDict
import unittest
from mock import Mock

from malcolm.core import Table
from malcolm.core.vmetas import BooleanArrayMeta, NumberArrayMeta, TableMeta
from malcolm.modules.pandablocks.parts.pandablockstablepart import \
    PandABlocksTablePart


class PandABoxTablePartTest(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        fields = OrderedDict()
        fields["NREPEATS"] = (7, 0)
        fields["INPUT_MASK"] = (32, 32)
        fields["TRIGGER_MASK"] = (48, 48)
        fields["TIME_PH_A"] = (95, 64)
        self.client.get_table_fields.return_value = fields
        self.meta = TableMeta("Seq table")
        self.o = PandABlocksTablePart(
            self.client, self.meta,
            block_name="SEQ1", field_name="TABLE", writeable=True)

    def test_init(self):
        assert list(self.meta.elements) == [
            "nrepeats", "inputMask", "triggerMask", "timePhA"]
        self.assertIsInstance(self.meta.elements["nrepeats"], NumberArrayMeta)
        assert self.meta.elements["nrepeats"].dtype == "uint8"
        assert self.meta.elements["nrepeats"].tags == ("widget:textinput",)
        self.assertIsInstance(self.meta.elements["inputMask"], BooleanArrayMeta)
        assert self.meta.elements["inputMask"].tags == ("widget:checkbox",)
        self.assertIsInstance(self.meta.elements["triggerMask"], BooleanArrayMeta)
        assert self.meta.elements["triggerMask"].tags == ("widget:checkbox",)
        self.assertIsInstance(self.meta.elements["timePhA"], NumberArrayMeta)
        assert self.meta.elements["timePhA"].dtype == "uint32"
        assert self.meta.elements["timePhA"].tags == ("widget:textinput",)

    def test_list_from_table(self):
        table = Table(self.meta)
        table.append([32, True, True, 4294967295])
        table.append([0, True, False, 1])
        table.append([0, False, False, 0])
        l = self.o.list_from_table(table)
        assert l == (
                         [32, 0x10001, 4294967295,
                         0, 0x1, 1,
                         0, 0x0, 0])

    def test_table_from_list(self):
        l = [32, 0x10001, 4294967295,
             0, 0x1, 1,
             0, 0x0, 0]
        table = self.o.table_from_list(l)
        assert list(table.nrepeats) == [32, 0, 0]
        assert list(table.inputMask) == [True, True, False]
        assert list(table.triggerMask) == [True, False, False]
        assert list(table.timePhA) == [4294967295, 1, 0]


if __name__ == "__main__":
    unittest.main(verbosity=2)
