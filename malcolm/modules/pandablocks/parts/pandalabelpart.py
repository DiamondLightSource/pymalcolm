from annotypes import Anno

from malcolm.modules import builtin

from ..util import AClient

with Anno("The field of *METADATA to set when label is changed"):
    AMetadataField = str
ALabelValue = builtin.parts.ALabelValue


class PandALabelPart(builtin.parts.LabelPart):
    def __init__(
        self, client: AClient, metadata_field: AMetadataField, value: ALabelValue
    ) -> None:
        super().__init__(value)
        self.client = client
        self.metadata_field = metadata_field

    def handle_change(self, value, ts):
        if not value:
            value = self.initial_value
        super().set_label(value, ts)

    def set_label(self, value, ts=None):
        super().set_label(value, ts)
        self.client.set_field("*METADATA", self.metadata_field, self.attr.value)
