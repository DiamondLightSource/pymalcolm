from annotypes import Anno

from malcolm.modules import builtin
from ..util import AClient

with Anno("The field of *METADATA to set when label is changed"):
    AMetadataField = str
ALabelValue = builtin.parts.ALabelValue


class PandALabelPart(builtin.parts.LabelPart):
    def __init__(self, client, metedata_field, value):
        # type: (AClient, AMetadataField, ALabelValue) -> None
        super(PandALabelPart, self).__init__(value)
        self.client = client
        self.metedata_field = metedata_field

    def handle_change(self, value, ts):
        if value:
            super(PandALabelPart, self).set_label(value, ts)

    def set_label(self, value, ts=None):
        self.client.set_field("*METADATA", self.metedata_field, value)
        super(PandALabelPart, self).set_label(value, ts)
