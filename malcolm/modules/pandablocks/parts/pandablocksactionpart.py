from malcolm.core import Part, MethodModel, snake_to_camel


class PandABlocksActionPart(Part):
    """This will normally be instantiated by the PandABox assembly, not created
    in yaml"""

    def __init__(self, client, block_name, field_name, description, tags):
        super(PandABlocksActionPart, self).__init__(field_name)
        self.client = client
        self.block_name = block_name
        self.field_name = field_name
        self.description = description
        self.tags = tags
        self.arg_name = None
        self.method = None

    def create_method_models(self):
        method_name = snake_to_camel(self.field_name)
        self.method = MethodModel()
        self.method.set_description(self.description)
        self.method.set_tags(self.tags)
        yield method_name, self.method, self.set_field

    def set_field(self):
        self.client.set_field(self.block_name, self.field_name, "")

