from malcolm.core import Part, method_takes, REQUIRED, MethodModel, \
    snake_to_camel


class PandABlocksActionPart(Part):
    """This will normally be instantiated by the PandABox assembly, not created
    in yaml"""

    def __init__(self, client, block_name, field_name, description, tags,
                 arg_meta=None):
        super(PandABlocksActionPart, self).__init__(field_name)
        self.client = client
        self.block_name = block_name
        self.field_name = field_name
        self.description = description
        self.tags = tags
        self.arg_name = None
        self.arg_meta = arg_meta
        self.method = None

    def create_method_models(self):
        method_name = snake_to_camel(self.field_name)
        if self.arg_meta:
            self.arg_name = method_name

            # Decorate set_field with a Method
            @method_takes(self.arg_name, self.arg_meta, REQUIRED)
            def set_field(params):
                self.set_field(params)

            self.method = set_field.MethodModel
            writeable_func = set_field
        else:
            self.method = MethodModel()
            writeable_func = None
        self.method.set_description(self.description)
        self.method.set_tags(self.tags)
        yield method_name, self.method, writeable_func

    def set_field(self, params=None):
        if params is None:
            value = 0
        else:
            value = params[self.arg_name]
        self.client.set_field(self.block_name, self.field_name, value)

