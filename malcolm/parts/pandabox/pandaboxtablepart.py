from collections import OrderedDict

from malcolm.core.vmetas import NumberArrayMeta, BooleanArrayMeta
from malcolm.core import TableElementMap
from malcolm.parts.pandabox.pandaboxfieldpart import PandABoxFieldPart


class PandABoxTablePart(PandABoxFieldPart):
    """This will normally be instantiated by the PandABox assembly, not created
    in yaml"""

    def __init__(self, process, control, meta, block_name, field_name,
                 writeable):
        super(PandABoxTablePart, self).__init__(
            process, control, meta, block_name, field_name, writeable)
        # Fill in the meta object with the correct headers
        columns = OrderedDict()
        self.fields = control.get_table_fields(block_name, field_name)
        for name, (bits_hi, bits_lo) in self.fields.items():
            nbits = bits_hi - bits_lo
            if nbits < 1:
                raise ValueError("Bad bits %s:%s" % (bits_hi, bits_lo))
            if nbits == 1:
                column_meta = BooleanArrayMeta(name)
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
                column_meta = NumberArrayMeta(dtype, name)
            columns[name] = column_meta
        meta.set_elements(TableElementMap(columns))

    def set_field(self, value):
        # TODO: this is not right, should be arrays
        full_field = "%s.%s" % (self.block_name, self.field_name)
        int_values = []
        for row in range(len(value[list(self.fields)[0]])):
            int_value = 0
            for name, (bits_hi, bits_lo) in self.fields.items():
                bit_value = value[name] & 2 ** (bits_hi - bits_lo)
                int_value |= bit_value << bits_lo
            int_values.append(int_value)
        self.control.set_table(full_field, int_values)

