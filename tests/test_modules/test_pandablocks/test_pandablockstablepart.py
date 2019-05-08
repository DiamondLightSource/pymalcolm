from collections import OrderedDict
import unittest
from mock import Mock

from malcolm.core import BooleanArrayMeta, NumberArrayMeta, TableMeta, \
    ChoiceArrayMeta
from malcolm.modules.pandablocks.pandablocksclient import TableFieldData
from malcolm.modules.pandablocks.parts.pandatablepart import \
    PandATablePart


class PandABoxTablePartTest(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        fields = OrderedDict()
        fields["NREPEATS"] = TableFieldData(7, 0, "Num Repeats", None)
        fields["SWITCH"] = TableFieldData(34, 32, "Choices", ["A", "b", "CC"])
        fields["TRIGGER_MASK"] = TableFieldData(48, 48, "Trigger Mask", None)
        fields["TIME_PH_A"] = TableFieldData(95, 64, "Time Phase A", None)
        self.client.get_table_fields.return_value = fields
        self.meta = TableMeta("Seq table", writeable=True)
        self.o = PandATablePart(
            self.client, self.meta,
            block_name="SEQ1", field_name="TABLE")

    def test_init(self):
        assert list(self.meta.elements) == [
            "nrepeats", "switch", "triggerMask", "timePhA"]
        self.assertIsInstance(self.meta.elements["nrepeats"], NumberArrayMeta)
        assert self.meta.elements["nrepeats"].dtype == "uint8"
        assert self.meta.elements["nrepeats"].tags == ["widget:textinput"]
        assert self.meta.elements["nrepeats"].description == "Num Repeats"
        self.assertIsInstance(self.meta.elements["switch"], ChoiceArrayMeta)
        assert self.meta.elements["switch"].tags == ["widget:combo"]
        assert self.meta.elements["switch"].description == "Choices"
        assert self.meta.elements["switch"].choices == ["A", "b", "CC"]
        self.assertIsInstance(self.meta.elements["triggerMask"],
                              BooleanArrayMeta)
        assert self.meta.elements["triggerMask"].tags == ["widget:checkbox"]
        assert self.meta.elements["triggerMask"].description == "Trigger Mask"
        self.assertIsInstance(self.meta.elements["timePhA"], NumberArrayMeta)
        assert self.meta.elements["timePhA"].dtype == "uint32"
        assert self.meta.elements["timePhA"].tags == ["widget:textinput"]
        assert self.meta.elements["timePhA"].description == "Time Phase A"

    def test_list_from_table(self):
        table = self.meta.table_cls.from_rows([
            [32, "b", True, 4294967295],
            [0, "b", False, 1],
            [0, "A", False, 0]
        ])
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
        assert list(table.switch) == ["b", "b", "A"]
        assert list(table.triggerMask) == [True, False, False]
        assert list(table.timePhA) == [4294967295, 1, 0]


if __name__ == "__main__":
    unittest.main(verbosity=2)
