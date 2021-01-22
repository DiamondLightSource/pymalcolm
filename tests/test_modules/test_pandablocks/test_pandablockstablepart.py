import unittest
from collections import OrderedDict

from mock import Mock

from malcolm.core import BooleanArrayMeta, ChoiceArrayMeta, NumberArrayMeta, TableMeta
from malcolm.modules.pandablocks.pandablocksclient import TableFieldData
from malcolm.modules.pandablocks.parts.pandatablepart import PandATablePart


class PandABoxTablePartTest(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        fields = OrderedDict()
        fields["NREPEATS"] = TableFieldData(15, 0, "Num Repeats", None, False)
        fields["TRIGGER"] = TableFieldData(19, 16, "Choices", ["A", "b", "CC"], False)
        fields["POSITION"] = TableFieldData(63, 32, "Position", None, True)
        fields["TIME1"] = TableFieldData(95, 64, "Time Phase A", None, False)
        fields["OUTA1"] = TableFieldData(20, 20, "Out1", None, False)
        fields["TIME2"] = TableFieldData(127, 96, "Time Phase B", None, False)
        fields["OUTA2"] = TableFieldData(26, 26, "Out2", None, False)
        self.client.get_table_fields.return_value = fields
        self.meta = TableMeta("Seq table", writeable=True)
        self.o = PandATablePart(
            self.client, self.meta, block_name="SEQ1", field_name="TABLE"
        )

    def assert_meta(self, meta, cls, **attrs):
        self.assertIsInstance(meta, cls)
        for k, v in attrs.items():
            assert meta[k] == v

    def test_init(self):
        assert list(self.meta.elements) == [
            "nrepeats",
            "trigger",
            "position",
            "time1",
            "outa1",
            "time2",
            "outa2",
        ]
        self.assert_meta(
            self.meta.elements["nrepeats"],
            NumberArrayMeta,
            dtype="uint16",
            tags=["widget:textinput"],
            description="Num Repeats",
        )
        self.assert_meta(
            self.meta.elements["trigger"],
            ChoiceArrayMeta,
            tags=["widget:combo"],
            description="Choices",
            choices=["A", "b", "CC"],
        )
        self.assert_meta(
            self.meta.elements["position"],
            NumberArrayMeta,
            dtype="int32",
            tags=["widget:textinput"],
            description="Position",
        )
        self.assert_meta(
            self.meta.elements["time1"],
            NumberArrayMeta,
            dtype="uint32",
            tags=["widget:textinput"],
            description="Time Phase A",
        )
        self.assert_meta(
            self.meta.elements["outa1"],
            BooleanArrayMeta,
            tags=["widget:checkbox"],
            description="Out1",
        )
        self.assert_meta(
            self.meta.elements["time2"],
            NumberArrayMeta,
            dtype="uint32",
            tags=["widget:textinput"],
            description="Time Phase B",
        )
        self.assert_meta(
            self.meta.elements["outa2"],
            BooleanArrayMeta,
            tags=["widget:checkbox"],
            description="Out2",
        )

    def test_list_from_table(self):
        table = self.meta.validate(
            self.meta.table_cls.from_rows(
                [
                    [32, "b", -1, 4096, True, 4097, False],
                    [0, "b", 1, 0, False, 200, True],
                    [0, "CC", 0, 6, True, 200, False],
                ]
            )
        )
        li = self.o.list_from_table(table)
        assert all(
            li
            == (
                [
                    0x00110020,
                    4294967295,
                    4096,
                    4097,
                    0x04010000,
                    1,
                    0,
                    200,
                    0x00120000,
                    0,
                    6,
                    200,
                ]
            )
        )

    def test_table_from_list(self):
        li = [
            0x00110020,
            4294967295,
            4096,
            4097,
            0x04010000,
            1,
            0,
            200,
            0x00120000,
            0,
            6,
            200,
        ]
        table = self.o.table_from_list([str(x) for x in li])
        assert table.nrepeats == [32, 0, 0]
        assert table.trigger == ["b", "b", "CC"]
        assert table.position == [-1, 1, 0]
        assert table.time1 == [4096, 0, 6]
        assert table.outa1 == [True, False, True]
        assert table.time2 == [4097, 200, 200]
        assert table.outa2 == [False, True, False]


if __name__ == "__main__":
    unittest.main(verbosity=2)
