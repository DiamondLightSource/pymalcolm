from malcolm.core import Part, snake_to_camel
from malcolm.modules.builtin.vmetas import BooleanMeta


class PandABlocksFieldPart(Part):
    """This will normally be instantiated by the PandABox assembly, not created
    in yaml"""

    def __init__(self, client, meta, block_name, field_name, writeable,
                 initial_value=None):
        super(PandABlocksFieldPart, self).__init__(field_name)
        self.client = client
        self.meta = meta
        self.block_name = block_name
        self.field_name = field_name
        self.writeable = writeable
        self.initial_value = initial_value
        self.attr = None

    def create_attribute_models(self):
        attr_name = snake_to_camel(self.field_name.replace(".", "_"))
        self.attr = self.meta.create_attribute_model(self.initial_value)
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
        self.client.set_field(self.block_name, self.field_name, value)
        # self.attr.set_value(value)

