from malcolm.core import Part, method_takes, REQUIRED, MethodMeta
from malcolm.parts.pandabox.pandaboxutil import make_label_attr_name


class PandABoxActionPart(Part):
    """This will normally be instantiated by the PandABox assembly, not created
    in yaml"""

    def __init__(self, process, control, block_name, field_name, description,
                 tags, arg_meta=None):
        params = Part.MethodMeta.prepare_input_map(name=field_name)
        super(PandABoxActionPart, self).__init__(process, params)
        self.control = control
        self.block_name = block_name
        self.field_name = field_name
        self.description = description
        self.tags = tags
        self.arg_name = None
        self.arg_meta = arg_meta
        self.method = None

    def create_methods(self):
        label, method_name = make_label_attr_name(self.field_name)
        if self.arg_meta:
            self.arg_name = method_name

            # Decorate set_field with a Method
            @method_takes(self.arg_name, self.arg_meta, REQUIRED)
            def set_field(params):
                self.set_field(params)

            self.method = set_field.MethodMeta
            writeable_func = set_field
        else:
            self.method = MethodMeta()
            writeable_func = None
        self.method.set_description(self.description)
        self.method.set_tags(self.tags)
        self.method.set_label(label)
        yield method_name, self.method, writeable_func

    def set_field(self, params=None):
        if params is None:
            value = 0
        else:
            value = params[self.arg_name]
        self.control.set_field(self.block_name, self.field_name, value)

