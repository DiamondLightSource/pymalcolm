from malcolm.core import Part
from malcolm.vmetas.builtin import BooleanMeta
from .pandablocksutil import make_label_attr_name


class PandABlocksFieldPart(Part):
    """This will normally be instantiated by the PandABox assembly, not created
    in yaml"""

    def __init__(self, child, meta, block_name, field_name, writeable,
                 initial_value=None):
        super(PandABlocksFieldPart, self).__init__(field_name)
        self.child = child
        self.meta = meta
        self.block_name = block_name
        self.field_name = field_name
        self.writeable = writeable
        self.initial_value = initial_value
        self.attr = None

    def create_attributes(self):
        label, attr_name = make_label_attr_name(self.field_name)
        self.meta.set_label(label)
        self.attr = self.meta.create_attribute(self.initial_value)
        if self.writeable:
            writeable_func = self.set_field
        else:
            writeable_func = None
        yield attr_name, self.attr, writeable_func

    def set_field(self, value):
        # TODO: goes in the server
        if hasattr(self.meta, "choices"):
            if len(self.meta.choices) <= 32:
                if value == "ZERO":
                    value = "POSITIONS.ZERO"
            else:
                if value == "ZERO":
                    value = "BITS.ZERO"
                elif value == "ONE":
                    value = "BITS.ONE"
        elif isinstance(self.meta, BooleanMeta):
            value = int(value)
        self.child.set_field(self.block_name, self.field_name, value)

