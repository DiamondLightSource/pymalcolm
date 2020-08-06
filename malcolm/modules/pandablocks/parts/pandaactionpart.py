from typing import Optional, Sequence, Union

from annotypes import Anno, Array

from malcolm.core import MethodModel, Part, PartRegistrar, snake_to_camel

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
    ATags = Union[Array[str]]
UTags = Union[ATags, Sequence[str], str]


class PandAActionPart(Part):
    """This will normally be instantiated by the PandABox assembly, not created
    in yaml"""

    def __init__(
        self,
        client: AClient,
        block_name: ABlockName,
        field_name: AFieldName,
        description: ADescription,
        tags: UTags,
    ) -> None:
        super().__init__(field_name)
        self.client = client
        self.block_name = block_name
        self.field_name = field_name
        self.description = description
        self.tags = tags
        self.method: Optional[MethodModel] = None

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        method_name = snake_to_camel(self.field_name)
        self.method = registrar.add_method_model(
            self.set_field, method_name, self.description
        )
        self.method.meta.set_tags(self.tags)

    def set_field(self):
        self.client.set_field(self.block_name, self.field_name, "")
