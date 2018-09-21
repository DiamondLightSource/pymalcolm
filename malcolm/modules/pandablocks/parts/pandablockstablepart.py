from malcolm.compat import OrderedDict
from malcolm.core import snake_to_camel, camel_to_title, Widget, \
    BooleanArrayMeta, NumberArrayMeta, ChoiceArrayMeta
from .pandablocksfieldpart import PandABlocksFieldPart, AClient, AMeta, \
    ABlockName, AFieldName
from ..pandablocksclient import TableFieldData


class PandABlocksTablePart(PandABlocksFieldPart):
    """This will normally be instantiated by the PandABox assembly, not created
    in yaml"""

    def __init__(self, client, meta, block_name, field_name):
        # type: (AClient, AMeta, ABlockName, AFieldName) -> None
        # Fill in the meta object with the correct headers
        columns = OrderedDict()
        self.field_data = OrderedDict()
        fields = client.get_table_fields(block_name, field_name)
        if not fields:
            # Didn't put any metadata in, make some up
            fields["VALUE"] = TableFieldData(31, 0, "The Value", None)
        for column_name, field_data in fields.items():
            nbits = field_data.bits_hi - field_data.bits_lo + 1
            if nbits < 1:
                raise ValueError("Bad bits in %s" % (field_data,))
            if field_data.labels:
                column_meta = ChoiceArrayMeta(choices=field_data.labels)
                widget = Widget.COMBO
            elif nbits == 1:
                column_meta = BooleanArrayMeta()
                widget = Widget.CHECKBOX
            else:
                if nbits <= 8:
                    dtype = "uint8"
                elif nbits <= 16:
                    dtype = "uint16"
                elif nbits <= 32:
                    dtype = "uint32"
                elif nbits <= 64:
                    dtype = "uint64"
                else:
                    raise ValueError("Bad bits in %s" % (field_data,))
                column_meta = NumberArrayMeta(dtype)
                widget = Widget.TEXTINPUT
            column_name = snake_to_camel(column_name)
            column_meta.set_label(camel_to_title(column_name))
            column_meta.set_tags([widget.tag()])
            column_meta.set_description(field_data.description)
            column_meta.set_writeable(True)
            columns[column_name] = column_meta
            self.field_data[column_name] = field_data
        meta.set_elements(columns)
        # Superclass will make the attribute for us
        super(PandABlocksTablePart, self).__init__(
            client, meta, block_name, field_name)

    def set_field(self, value):
        int_values = self.list_from_table(value)
        self.client.set_table(self.block_name, self.field_name, int_values)

    def _calc_nconsume(self):
        max_bits_hi = max(f.bits_hi for f in self.field_data.values())
        nconsume = int((max_bits_hi + 31) / 32)
        return nconsume

    def list_from_table(self, table):
        int_values = []
        nconsume = self._calc_nconsume()
        for row in table.rows():
            int_value = 0
            for name, value in zip(table.call_types, row):
                field_data = self.field_data[name]
                max_value = 2 ** (field_data.bits_hi - field_data.bits_lo + 1)
                if field_data.labels:
                    field_value = field_data.labels.index(value)
                else:
                    field_value = int(value)
                assert field_value < max_value, \
                    "Expected %s[%d] < %s, got %s" % (
                        name, row, max_value, field_value)
                int_value |= field_value << field_data.bits_lo
            # Split the big int into 32-bit numbers
            for i in range(nconsume):
                int_values.append(int_value & (2 ** 32 - 1))
                int_value = int_value >> 32
        return int_values

    def table_from_list(self, int_values):
        rows = []
        nconsume = self._calc_nconsume()
        for i in range(int(len(int_values) / nconsume)):
            int_value = 0
            for c in range(nconsume):
                int_value += int(int_values[i*nconsume+c]) << (32 * c)
            row = []
            for name, field_data in self.field_data.items():
                mask = 2 ** (field_data.bits_hi + 1) - 1
                field_value = (int_value & mask) >> field_data.bits_lo
                if field_data.labels:
                    # This is a choice meta, so write the string value
                    row.append(field_data.labels[field_value])
                else:
                    row.append(field_value)
            rows.append(row)
        table = self.meta.table_cls.from_rows(rows)
        return table

