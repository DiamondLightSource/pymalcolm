from collections import OrderedDict

from malcolm.core.vmetas import NumberMeta, BooleanMeta
from malcolm.core import TableElementMap
from malcolm.parts.pandabox.pandaboxfieldpart import PandABoxFieldPart


class PandABoxTablePart(PandABoxFieldPart):
    """This will normally be instantiated by the PandABox assembly, not created
    in yaml"""

    def __init__(self, process, params, control, meta):
        super(PandABoxTablePart, self).__init__(process, params, control, meta)
        # Fill in the meta object with the correct headers
        columns = OrderedDict()
        self.fields = control.get_table_fields(
            params.block_name, params.field_name)
        for name, (bits_hi, bits_lo) in self.fields.items():
            nbits = bits_hi - bits_lo
            if nbits < 1:
                raise ValueError("Bad bits %s:%s" % (bits_hi, bits_lo))
            # TODO: what about time scaling?
            if nbits == 1:
                column_meta = BooleanMeta(name)
            else:
                if nbits <= 8:
                    dtype = "unit8"
                elif nbits <= 16:
                    dtype = "uint16"
                elif nbits <= 32:
                    dtype = "uint32"
                elif nbits <= 64:
                    dtype = "uint64"
                else:
                    raise ValueError("Bad bits %s:%s" % (bits_hi, bits_lo))
                column_meta = NumberMeta(dtype, name)
            columns[name] = column_meta
        meta.set_elements(TableElementMap(columns))

    def set_field(self, value):
        full_field = "%s.%s" % (self.params.block_name, self.params.field_name)
        int_value = 0
        for name, (bits_hi, bits_lo) in self.fields.items():
            bit_value = value[name] & 2 ** (bits_hi - bits_lo)
            int_value |= bit_value << bits_lo
        self.control.set_field(full_field, int_value)
