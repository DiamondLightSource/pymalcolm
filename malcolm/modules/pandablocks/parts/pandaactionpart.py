from annotypes import Anno, Sequence, Array, Union

from malcolm.core import Part, snake_to_camel, PartRegistrar
from ..pandablocksclient import PandABlocksClient

with Anno("Client for setting and getting field"):
    AClient = PandABlocksClient
with Anno("Name of Block in TCP server"):
    ABlockName = str
with Anno("Name of Field in TCP server"):
    AFieldName = str
with Anno("Description for the Method"):
    ADescription = str
with Anno("Tags to be attached to Method"):
    ATags = Array[str]
UTags = Union[ATags, Sequence[str], str]


class PandAActionPart(Part):
    """This will normally be instantiated by the PandABox assembly, not created
    in yaml"""

    def __init__(self, client, block_name, field_name, description, tags):
        # type: (AClient, ABlockName, AFieldName, ADescription, UTags) -> None
        super(PandAActionPart, self).__init__(field_name)
        self.client = client
        self.block_name = block_name
        self.field_name = field_name
        self.description = description
        self.tags = tags
        self.method = None

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(PandAActionPart, self).setup(registrar)
        method_name = snake_to_camel(self.field_name)
        self.method = registrar.add_method_model(
            self.set_field, method_name, self.description)
        self.method.meta.set_tags(self.tags)

    def set_field(self):
        self.client.set_field(self.block_name, self.field_name, "")

