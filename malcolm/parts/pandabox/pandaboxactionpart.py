from malcolm.core import Part, method_takes, REQUIRED, MethodMeta
from malcolm.core.vmetas import StringMeta, BooleanMeta


@method_takes(
    "block_name", StringMeta("Name of block for send commands"), REQUIRED,
    "field_name", StringMeta("Name of field for send commands"), REQUIRED,
    "description", StringMeta("Description of action"), REQUIRED,
)
class PandABoxActionPart(Part):
    """This will normally be instantiated by the PandABox assembly, not created
    in yaml"""

    def __init__(self, process, params, control, arg_name=None, arg_meta=None):
        super(PandABoxActionPart, self).__init__(process, params)
        self.control = control
        self.arg_name = arg_name
        self.arg_meta = arg_meta
        self.method = None

    def create_methods(self):
        method_name = self.params.field_name.replace(".", ":")
        if self.takes_meta:
            # Decorate set_field with a MethodMeta
            self.method = method_takes(
                self.arg_name, self.takes_meta, REQUIRED)(
                self.set_field).MethodMeta
            writeable_func = self.set_field
        else:
            self.method = MethodMeta()
            writeable_func = None
        self.method.set_description(self.params.description)
        yield method_name, self.method, writeable_func

    def set_field(self, params=None):
        full_field = "%s.%s" % (self.params.block_name, self.params.field_name)
        if params is None:
            value = 0
        else:
            value = params[self.arg_name]
        self.control.set_field(full_field, value)

