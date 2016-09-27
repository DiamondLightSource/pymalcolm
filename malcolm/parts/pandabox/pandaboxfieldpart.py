from malcolm.core import Part, method_takes, REQUIRED, Attribute
from malcolm.core.vmetas import StringMeta, BooleanMeta


@method_takes(
    "block_name", StringMeta("Name of block for send commands"), REQUIRED,
    "field_name", StringMeta("Name of field for send commands"), REQUIRED,
    "writeable", BooleanMeta("Whether attribute is writeable"), REQUIRED,
)
class PandABoxFieldPart(Part):
    """This will normally be instantiated by the PandABox assembly, not created
    in yaml"""

    def __init__(self, process, params, control, meta):
        super(PandABoxFieldPart, self).__init__(process, params)
        self.control = control
        self.meta = meta
        self.attr = None

    def create_attributes(self):
        self.attr = Attribute(self.meta)
        attr_name = self.params.field_name.replace(".", ":")
        if self.params.writeable:
            writeable_func = self.set_field
        else:
            writeable_func = None
        yield attr_name, self.attr, writeable_func

    def set_field(self, value):
        full_field = "%s.%s" % (self.params.block_name, self.params.field_name)
        self.control.set_field(full_field, value)

