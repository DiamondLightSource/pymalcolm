from typing import Any, Dict, List, Optional, Type, Union

from malcolm.core import (
    Alarm,
    AMri,
    Part,
    PartRegistrar,
    Table,
    TableMeta,
    TimeStamp,
    config_tag,
)

from ..util import AClient, BitsTable, PositionCapture, PositionsTable


def update_column(
    column_changes: Dict[str, List[Any]], column: str, table_value: Table
) -> List[Any]:
    try:
        column_value = column_changes[column]
    except KeyError:
        column_array = getattr(table_value, column)
        try:
            # numpy array
            column_value = column_array.seq.copy()
        except AttributeError:
            # list
            column_value = column_array.seq[:]
        column_changes[column] = column_value
    return column_value


def make_updated_table(old_value: Table, column_changes: Dict[str, List[Any]]) -> Table:
    # Create new table from the old and changes
    d = {k: column_changes.get(k, getattr(old_value, k)) for k in old_value}
    new_value = old_value.__class__(**d)
    return new_value


class PandABussesPart(Part):
    # Tables to make metas from
    bits_table_cls: Type[BitsTable] = BitsTable
    positions_table_cls: Type[PositionsTable] = PositionsTable

    # Attributes
    bits = None
    positions = None

    def __init__(self, name: AMri, client: AClient) -> None:
        super().__init__(name)
        self._client = client
        # Row index lookups
        # {bit_name: index}
        self._bit_indexes: Dict[str, int] = {}
        # {pos_name: index}
        self._pos_indexes: Dict[str, int] = {}
        # {pos_index: value}
        self._pos_values: Dict[int, int] = {}
        # Forward and reverse bit lookups
        # {pcap_capture_field: [bit_index]}
        self._pcap_bit_indexes: Dict[str, List[int]] = {}
        # {bit_name: pcap_capture_field}
        self._bit_pcap_fields: Dict[str, str] = {}

    def setup(self, registrar: PartRegistrar) -> None:
        self.bits = TableMeta.from_table(
            self.bits_table_cls,
            "Current values and capture status of Bit fields",
            writeable=[
                x for x in self.bits_table_cls.call_types if x not in ("name", "value")
            ],
            extra_tags=[config_tag()],
        ).create_attribute_model()
        self.positions = TableMeta.from_table(
            self.positions_table_cls,
            "Current values, scaling, and capture status of Position fields",
            writeable=[
                x
                for x in self.positions_table_cls.call_types
                if x not in ("name", "value")
            ],
            extra_tags=[config_tag()],
        ).create_attribute_model()
        registrar.add_attribute_model("bits", self.bits, self.set_bits)
        registrar.add_attribute_model("positions", self.positions, self.set_positions)

    def get_column_changes(self, old: Table, new: Table) -> Dict[str, List[Any]]:
        column_changes: Dict[str, List[Any]] = {}
        lookup = {k: i for i, k in enumerate(old.name)}
        for i, name in enumerate(new.name):
            for k in old:
                if k not in ("name", "value"):
                    new_value = new[k][i]
                    # Lookup row index in actual table
                    try:
                        j = lookup[name]
                    except KeyError:
                        self.log.warning(f"Ignoring table row with name {name}")
                    else:
                        if old[k][j] != new_value:
                            # row changed
                            update_column(column_changes, k, old)[j] = new_value
        return column_changes

    def set_bits(self, value: BitsTable) -> None:
        assert self.bits, "No bits"
        column_changes = self.get_column_changes(self.bits.value, value)
        if "capture" in column_changes:
            # If capture changed, set PCAP bits
            field_values = {}
            for bit in value.name:
                capture = column_changes["capture"][self._bit_indexes[bit]]
                capture_field = self._bit_pcap_fields[bit]
                if capture:
                    # If told to capture, this trumps anything it currently
                    # holds
                    field_values[capture_field] = "Value"
                else:
                    # If not already set, set it to No
                    field_values.setdefault(capture_field, "No")
            self._client.set_fields(field_values)
        new_value = make_updated_table(self.bits.value, column_changes)
        self.bits.set_value(new_value)

    def set_positions(self, value: PositionsTable) -> None:
        assert self.positions, "No positions"
        column_changes = self.get_column_changes(self.positions.value, value)
        for attr in ("capture", "scale", "offset", "units"):
            if attr in column_changes:
                # If attribute changed, set field bits
                field_values = {}
                for i, name in enumerate(self.positions.value.name):
                    field = "%s.%s" % (name, attr.upper())
                    value = column_changes[attr][i]
                    if attr == "capture":
                        # Convert Enum to string value for capture string
                        value = value.value
                    field_values[field] = value
                self._client.set_fields(field_values)
        new_value = make_updated_table(self.positions.value, column_changes)
        self.positions.set_value(new_value)

    @staticmethod
    def _make_initial_bits_table(bit_names: List[str]) -> BitsTable:
        bits_table = BitsTable(
            name=bit_names,
            value=[False] * len(bit_names),
            capture=[False] * len(bit_names),
        )
        return bits_table

    @staticmethod
    def _make_initial_pos_table(pos_names: List[str]) -> PositionsTable:
        pos_table = PositionsTable(
            name=pos_names,
            value=[0.0] * len(pos_names),
            units=[""] * len(pos_names),
            scale=[1.0] * len(pos_names),
            offset=[0.0] * len(pos_names),
            capture=[PositionCapture.NO] * len(pos_names),
        )
        return pos_table

    def create_busses(
        self, pcap_bits_fields: Dict[str, List[str]], pos_names: List[str]
    ) -> None:
        # Bits
        bit_names: List[str] = []
        self._bit_indexes = {}
        self._pcap_bit_indexes = {}
        self._bit_pcap_fields = {}
        for k, v in pcap_bits_fields.items():
            indexes = []
            for bit in v:
                if bit:
                    self._bit_pcap_fields[bit] = k
                    index = len(bit_names)
                    indexes.append(index)
                    bit_names.append(bit)
                    self._bit_indexes[bit] = index
            self._pcap_bit_indexes[k] = indexes
        assert self.bits, "No bits"
        self.bits.set_value(self._make_initial_bits_table(bit_names))
        # Positions
        assert self.positions, "No positions"
        self.positions.set_value(self._make_initial_pos_table(pos_names))
        # Pos lookups
        self._pos_indexes = {k: i for i, k in enumerate(pos_names)}
        for i, k in enumerate(pos_names):
            for suffix in ("CAPTURE", "SCALE", "OFFSET", "UNITS"):
                self._pos_indexes["%s.%s" % (k, suffix)] = i
            self._pos_values[i] = 0

    def _handle_bit(
        self, field_name: str, value: bool, column_changes: Dict[str, List[Any]]
    ) -> Optional[bool]:
        i = self._bit_indexes.get(field_name, None)
        assert self.bits, "No bits"
        if i is not None:
            # It's a bit, update the table changes
            update_column(column_changes, "value", self.bits.value)[i] = value
            return True
        return None

    def _handle_pos(
        self, field_name: str, value: str, column_changes: Dict[str, List[Any]]
    ) -> Optional[bool]:
        i = self._pos_indexes.get(field_name, None)
        if i is not None:
            split = field_name.split(".")
            if len(split) == 2:
                # Value change
                self._pos_values[i] = int(value)
            else:
                # Another field change
                assert len(split) == 3, "Bad Pos field name: %s" % field_name
                column = split[-1].lower()
                parsed_value: Union[str, float, PositionCapture]
                if column in ("scale", "offset"):
                    parsed_value = float(value)
                elif column == "capture":
                    parsed_value = PositionCapture(value)
                else:
                    parsed_value = value
                if self.positions:
                    update_column(column_changes, column, self.positions.value)[
                        i
                    ] = parsed_value
            # Grab scale and offset
            assert self.positions, "No positions"
            table_value = self.positions.value
            scale = column_changes.get("scale", table_value.scale)[i]
            offset = column_changes.get("offset", table_value.offset)[i]

            # It's a pos, update the value column with what we know
            update_column(column_changes, "value", self.positions.value)[i] = (
                self._pos_values[i] * scale + offset
            )
            return True
        return None

    def _handle_pcap(
        self, field_name: str, value: str, column_changes: Dict[str, List[Any]]
    ) -> Optional[bool]:
        # This should be a pcap bits field...
        indexes = self._pcap_bit_indexes.get(field_name, None)
        assert self.bits, "No bits"
        if indexes is not None:
            capture = value != "No"
            for i in indexes:
                update_column(column_changes, "capture", self.bits.value)[i] = capture
            return True
        return None

    def handle_changes(self, changes: Dict[str, Any], ts: TimeStamp) -> None:
        bit_column_changes: Dict[str, Any] = {}
        pos_column_changes: Dict[str, Any] = {}
        for k, v in changes.items():
            assert (
                self._handle_bit(k, v, bit_column_changes)
                or self._handle_pos(k, v, pos_column_changes)
                or self._handle_pcap(k, v, bit_column_changes)
            ), ("Don't know how to handle %s" % k)
        # Update the tables
        assert self.bits, "No bits"
        if bit_column_changes:
            new_value = make_updated_table(self.bits.value, bit_column_changes)
            self.bits.set_value_alarm_ts(new_value, Alarm.ok, ts)
        assert self.positions, "No positions"
        if pos_column_changes:
            new_value = make_updated_table(self.positions.value, pos_column_changes)
            self.positions.set_value_alarm_ts(new_value, Alarm.ok, ts)
