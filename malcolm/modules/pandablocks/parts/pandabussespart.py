import numpy as np

from annotypes import TYPE_CHECKING

from malcolm.core import Part, TableMeta, PartRegistrar, config_tag, \
    TimeStamp, Table, AMri
from ..util import BitsTable, PositionsTable, AClient, PositionCapture

if TYPE_CHECKING:
    from typing import Dict, List, Any, Type, Optional


def update_column(column_changes, column, table_value):
    # type: (Dict[str, List[Any]], str, Table) -> List[Any]
    try:
        column_value = column_changes[column]
    except KeyError:
        try:
            # numpy array
            column_value = table_value[column].seq.copy()
        except AttributeError:
            # list
            column_value = table_value[column].seq[:]
        column_changes[column] = column_value
    return column_value


def get_column_changes(old, new, lookup):
    # type: (Table, Table) -> Dict[str, List[Any]]
    column_changes = {}
    for i, name in enumerate(new.name):
        for k in old:
            if k not in ("name", "value"):
                new_value = new[k][i]
                # Lookup row index in actual table
                j = lookup[name]
                if old[k][j] != new_value:
                    # row changed
                    update_column(column_changes, k, old)[j] = new_value
    return column_changes


def make_default_table(table_cls, names):
    # type: (Type[Table], List[str]) -> Table
    kwargs = {}
    for k, anno in table_cls.call_types.items():
        if k == "name":
            v = names
        elif anno.typ is PositionCapture:
            v = [PositionCapture.NO] * len(names)
        else:
            v = [anno.typ()] * len(names)
        kwargs[k] = v
    return table_cls(**kwargs)


def make_updated_table(old_value, column_changes):
    # type: (Table, Dict[str, List[Any]]) -> Table
    # Create new table from the old and changes
    d = {k: column_changes.get(k, old_value[k]) for k in old_value}
    new_value = old_value.__class__(**d)
    return new_value


class PandABussesPart(Part):
    # Attributes
    bits = None
    positions = None

    def __init__(self, name, client):
        # type: (AMri, AClient) -> None
        super(PandABussesPart, self).__init__(name)
        self._client = client
        # Row index lookups
        # {bit_name: index}
        self._bit_indexes = {}
        # {pos_name: index}
        self._pos_indexes = {}
        # {pos_index: value}
        self._pos_values = {}
        # Forward and reverse bit lookups
        # {pcap_capture_field: [bit_index]}
        self._pcap_bit_indexes = {}
        # {bit_name: pcap_capture_field}
        self._bit_pcap_fields = {}

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.bits = self._make_bits_table()
        self.positions = self._make_positions_table()
        registrar.add_attribute_model(
            "bits", self.bits, self.set_bits)
        registrar.add_attribute_model(
            "positions", self.positions, self.set_positions)

    def _make_bits_table(self):
        meta = TableMeta.from_table(
            BitsTable, "Current values and capture status of Bit fields",
            writeable=("capture",), extra_tags=[config_tag()]
        )
        return meta.create_attribute_model()

    def _make_positions_table(self):
        meta = TableMeta.from_table(
            PositionsTable,
            "Current values, scaling, and capture status of Position fields",
            writeable=("scale", "offset", "units", "capture"),
            extra_tags=[config_tag()]
        )
        return meta.create_attribute_model()

    def set_bits(self, value):
        # type: (BitsTable) -> None
        column_changes = get_column_changes(
            self.bits.value, value, self._bit_indexes)
        if "capture" in column_changes:
            # If capture changed, set PCAP bits
            field_values = {k: "No" for k in self._pcap_bit_indexes}
            bit_names = self.bits.value.name
            for bit, capture in zip(bit_names, column_changes["capture"]):
                if capture:
                    capture_field = self._bit_pcap_fields[bit]
                    field_values[capture_field] = "Value"
            self._client.set_fields(field_values)
        if column_changes:
            new_value = make_updated_table(self.bits.value, column_changes)
            self.bits.set_value(new_value)

    def set_positions(self, value):
        # type: (PositionsTable) -> None
        column_changes = get_column_changes(
            self.positions.value, value, self._pos_indexes)
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
        if column_changes:
            new_value = make_updated_table(self.positions.value, column_changes)
            self.positions.set_value(new_value)

    def create_busses(self, pcap_bits_fields, pos_names):
        # type: (Dict[str, List[str]], List[str]) -> None
        # Bits
        bit_names = []
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
        self.bits.set_value(
            make_default_table(self.bits.meta.table_cls, bit_names))

        # Positions
        self.positions.set_value(
            make_default_table(self.positions.meta.table_cls, pos_names))
        # Pos lookups
        self._pos_indexes = {k: i for i, k in enumerate(pos_names)}
        for i, k in enumerate(pos_names):
            for suffix in ("CAPTURE", "SCALE", "OFFSET", "UNITS"):
                self._pos_indexes["%s.%s" % (k, suffix)] = i
            self._pos_values[i] = 0

    def _handle_bit(self, field_name, value, column_changes):
        # type: (str, bool, Dict[str, List[Any]]) -> Optional[bool]
        i = self._bit_indexes.get(field_name, None)
        if i is not None:
            # It's a bit, update the table changes
            update_column(column_changes, "value", self.bits.value)[i] = value
            return True

    def _handle_pos(self, field_name, value, column_changes):
        # type: (str, str, Dict[str, List[Any]]) -> Optional[bool]
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
                if column in ("scale", "offset"):
                    value = float(value)
                elif column == "capture":
                    value = PositionCapture(value)
                update_column(column_changes, column, self.positions.value)[i] \
                    = value
            # Grab scale and offset
            table_value = self.positions.value
            scale = column_changes.get("scale", table_value.scale)[i]
            offset = column_changes.get("offset", table_value.offset)[i]

            # It's a pos, update the value column with what we know
            update_column(column_changes, "value", self.positions.value)[i] \
                = self._pos_values[i] * scale + offset
            return True

    def _handle_pcap(self, field_name, value, column_changes):
        # type: (str, str, Dict[str, List[Any]]) -> None
        # We are the last in the line, this should be a pcap bits field...
        capture = value != "No"
        for i in self._pcap_bit_indexes[field_name]:
            update_column(column_changes, "capture", self.bits.value)[i] \
                = capture

    def handle_changes(self, changes, ts):
        # type: (Dict[str, Any], TimeStamp) -> None
        bit_column_changes = {}
        pos_column_changes = {}
        for k, v in changes.items():
            self._handle_bit(k, v, bit_column_changes) or \
                self._handle_pos(k, v, pos_column_changes) or \
                self._handle_pcap(k, v, bit_column_changes)
        # Update the tables
        if bit_column_changes:
            new_value = make_updated_table(self.bits.value, bit_column_changes)
            self.bits.set_value(new_value, ts=ts)
        if pos_column_changes:
            new_value = make_updated_table(
                self.positions.value, pos_column_changes)
            self.positions.set_value(new_value, ts=ts)
