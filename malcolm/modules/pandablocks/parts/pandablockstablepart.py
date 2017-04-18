from malcolm.compat import OrderedDict
from malcolm.core import Table, snake_to_camel, camel_to_title
from malcolm.tags import widget
from malcolm.modules.builtin.vmetas import NumberArrayMeta, BooleanArrayMeta
from .pandablocksfieldpart import PandABlocksFieldPart


class PandABlocksTablePart(PandABlocksFieldPart):
    """This will normally be instantiated by the PandABox assembly, not created
    in yaml"""

    def __init__(self, client, meta, block_name, field_name, writeable):
        super(PandABlocksTablePart, self).__init__(
            client, meta, block_name, field_name, writeable)
        # Fill in the meta object with the correct headers
        columns = OrderedDict()
        self.fields = OrderedDict()
        fields = client.get_table_fields(block_name, field_name)
        for field_name, (bits_hi, bits_lo) in fields.items():
            nbits = bits_hi - bits_lo + 1
            if nbits < 1:
                raise ValueError("Bad bits %s:%s" % (bits_hi, bits_lo))
            if nbits == 1:
                column_meta = BooleanArrayMeta(field_name)
                widget_tag = widget("checkbox")
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
                    raise ValueError("Bad bits %s:%s" % (bits_hi, bits_lo))
                column_meta = NumberArrayMeta(dtype, field_name)
                widget_tag = widget("textinput")
            column_name = snake_to_camel(field_name)
            column_meta.set_label(camel_to_title(column_name))
            column_meta.set_tags([widget_tag])
            columns[column_name] = column_meta
            self.fields[column_name] = (bits_hi, bits_lo)
        meta.set_elements(columns)

    def set_field(self, value):
        int_values = self.list_from_table(value)
        self.client.set_table(self.block_name, self.field_name, int_values)

    def _calc_nconsume(self):
        max_bits_hi = max(self.fields.values())[0]
        nconsume = int((max_bits_hi + 31) / 32)
        return nconsume

    def list_from_table(self, table):
        int_values = []
        if self.fields:
            nconsume = self._calc_nconsume()
            for row in range(len(table[list(self.fields)[0]])):
                int_value = 0
                for name, (bits_hi, bits_lo) in self.fields.items():
                    max_value = 2 ** (bits_hi - bits_lo + 1)
                    field_value = int(table[name][row])
                    assert field_value < max_value, \
                        "Expected %s[%d] < %s, got %s" % (
                            name, row, max_value, field_value)
                    int_value |= field_value << bits_lo
                # Split the big int into 32-bit numbers
                for i in range(nconsume):
                    int_values.append(int_value & (2 ** 32 - 1))
                    int_value = int_value >> 32
        return int_values

    def table_from_list(self, int_values):
        table = Table(self.meta)
        if self.fields:
            nconsume = self._calc_nconsume()

            for i in range(int(len(int_values) / nconsume)):
                int_value = 0
                for c in range(nconsume):
                    int_value += int(int_values[i*nconsume+c]) << (32 * c)
                row = []
                for name, (bits_hi, bits_lo) in self.fields.items():
                    mask = 2 ** (bits_hi + 1) - 1
                    field_value = (int_value & mask) >> bits_lo
                    row.append(field_value)
                table.append(row)
        return table

