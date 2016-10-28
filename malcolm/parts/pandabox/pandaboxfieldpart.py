from malcolm.core import Part


class PandABoxFieldPart(Part):
    """This will normally be instantiated by the PandABox assembly, not created
    in yaml"""

    def __init__(self, process, control, meta, block_name, field_name,
                 writeable, initial_value=None):
        params = Part.MethodMeta.prepare_input_map(name=field_name)
        super(PandABoxFieldPart, self).__init__(process, params)
        self.control = control
        self.meta = meta
        self.label = field_name.replace(".", " ").replace("_", " ").title()
        self.meta.set_label(self.label)
        self.block_name = block_name
        self.field_name = field_name
        self.writeable = writeable
        self.initial_value = initial_value
        self.attr = None

    def create_attributes(self):
        self.attr = self.meta.make_attribute(self.initial_value)
        attr_name = self.label.replace(" ", "")
        attr_name = attr_name[0].lower() + attr_name[1:]
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
        self.control.set_field(self.block_name, self.field_name, value)

