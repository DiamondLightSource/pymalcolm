import unittest
from collections import OrderedDict

from mock import MagicMock, call

from malcolm.core import TimeStamp
from malcolm.modules.pandablocks.parts.pandabussespart import PandABussesPart
from malcolm.modules.pandablocks.util import BitsTable, PositionCapture, PositionsTable


class PandABussesPartTest(unittest.TestCase):
    def setUp(self):
        self.o = PandABussesPart("busses", MagicMock())
        self.o.setup(MagicMock())
        pcap_bits_fields = OrderedDict()
        pcap_bits_fields["PCAP.BITS0.CAPTURE"] = ["B1.B%d" % i for i in range(6)]
        pcap_bits_fields["PCAP.BITS1.CAPTURE"] = [
            "B2.B%d" % i for i in range(12, 15)
        ] + [""] * 12
        pos_names = ["B1.P%d" % i for i in range(3)] + ["B2.P33"]
        self.o.create_busses(pcap_bits_fields, pos_names)
        self.expected_bit_names = [
            "B1.B0",
            "B1.B1",
            "B1.B2",
            "B1.B3",
            "B1.B4",
            "B1.B5",
            "B2.B12",
            "B2.B13",
            "B2.B14",
        ]
        self.expected_pos_names = ["B1.P0", "B1.P1", "B1.P2", "B2.P33"]

    def test_init(self):
        assert list(self.o.bits.meta.elements) == ["name", "value", "capture"]
        assert self.o.bits.value.name == self.expected_bit_names
        assert self.o.bits.value.value == [False] * 9
        assert self.o.bits.value.value.seq.dtype == bool
        assert self.o.bits.value.capture == [False] * 9
        assert self.o.bits.meta.elements["capture"].tags == ["widget:checkbox"]
        assert list(self.o.positions.meta.elements) == [
            "name",
            "value",
            "units",
            "scale",
            "offset",
            "capture",
        ]
        assert self.o.positions.value.name == self.expected_pos_names
        assert self.o.positions.value.value == [0.0] * 4
        assert self.o.positions.value.value.seq.dtype == float
        assert self.o.positions.value.units == [""] * 4
        assert self.o.positions.value.scale == [1.0] * 4
        assert self.o.positions.value.offset == [0.0] * 4
        assert self.o.positions.value.capture == [PositionCapture.NO] * 4

    def test_scale_offset(self):
        ts = TimeStamp()
        changes = {"B1.P0.SCALE": "32", "B1.P0.OFFSET": "0.1", "B1.P0": "100"}
        self.o.handle_changes(changes, ts)
        assert self.o.positions.timeStamp is ts
        assert list(self.o.positions.value.rows())[0] == [
            "B1.P0",
            3200.1,
            "",
            32.0,
            0.1,
            PositionCapture.NO,
        ]
        self.o.handle_changes({"B1.P0.SCALE": "64"}, ts)
        assert list(self.o.positions.value.rows())[0] == [
            "B1.P0",
            6400.1,
            "",
            64.0,
            0.1,
            PositionCapture.NO,
        ]
        self.o.handle_changes({"B1.P0": "200"}, ts)
        assert list(self.o.positions.value.rows())[0] == [
            "B1.P0",
            12800.1,
            "",
            64.0,
            0.1,
            PositionCapture.NO,
        ]

    def test_pos_capture(self):
        ts = TimeStamp()
        changes = {"B1.P2.CAPTURE": "Min Max Mean", "B1.P2.SCALE": "1", "B1.P2": "100"}
        self.o.handle_changes(changes, ts)
        assert list(self.o.positions.value.rows())[2] == [
            "B1.P2",
            100,
            "",
            1.0,
            0.0,
            PositionCapture.MIN_MAX_MEAN,
        ]

    def test_pos_set_capture(self):
        value = PositionsTable(
            name=["B1.P2"],
            value=[23.0],
            units=["mm"],
            scale=[0.1],
            offset=[0.0],
            capture=[PositionCapture.MEAN],
        )
        self.o.set_positions(value)
        assert self.o.positions.value.name == self.expected_pos_names
        assert self.o.positions.value.value == [0.0] * 4
        assert self.o.positions.value.units == ["", "", "mm", ""]
        assert self.o.positions.value.scale == [1.0, 1.0, 0.1, 1.0]
        assert self.o.positions.value.offset == [0.0, 0.0, 0.0, 0.0]
        assert self.o.positions.value.capture == [
            PositionCapture.NO,
            PositionCapture.NO,
            PositionCapture.MEAN,
            PositionCapture.NO,
        ]
        assert self.o._client.set_fields.call_args_list == [
            call(
                {
                    "B1.P2.CAPTURE": "Mean",
                    "B1.P1.CAPTURE": "No",
                    "B2.P33.CAPTURE": "No",
                    "B1.P0.CAPTURE": "No",
                }
            ),
            call(
                {
                    "B1.P0.SCALE": 1.0,
                    "B2.P33.SCALE": 1.0,
                    "B1.P1.SCALE": 1.0,
                    "B1.P2.SCALE": 0.1,
                }
            ),
            call(
                {
                    "B2.P33.UNITS": "",
                    "B1.P2.UNITS": "mm",
                    "B1.P1.UNITS": "",
                    "B1.P0.UNITS": "",
                }
            ),
        ]

    def test_bits(self):
        ts = TimeStamp()
        changes = {
            "B1.B1": True,
            "B1.B3": True,
        }
        self.o.handle_changes(changes, ts)
        assert self.o.bits.timeStamp is ts
        assert list(self.o.bits.value.rows())[1] == ["B1.B1", True, False]
        assert list(self.o.bits.value.rows())[2] == ["B1.B2", False, False]
        assert list(self.o.bits.value.rows())[3] == ["B1.B3", True, False]

    def test_bit_capture_change(self):
        ts = TimeStamp()
        changes = {"PCAP.BITS0.CAPTURE": "Value"}
        self.o.handle_changes(changes, ts)
        assert self.o.bits.value.capture == [True] * 6 + [False] * 3

    def test_bit_set_capture(self):
        value = BitsTable(name=["B1.B1"], value=[True], capture=[True])
        self.o.set_bits(value)
        assert self.o.bits.value.name == self.expected_bit_names
        assert self.o.bits.value.capture == [False, True] + [False] * 7
        assert self.o.bits.value.value == [False] * 9
        self.o._client.set_fields.assert_called_once_with(
            {"PCAP.BITS0.CAPTURE": "Value"}
        )
