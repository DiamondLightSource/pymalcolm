from malcolm.modules import builtin
from ..util import AClient, ABlockName

ASvg = builtin.parts.ASvg


class PandAIconPart(builtin.parts.IconPart):
    update_fields = set()

    def __init__(self, client, block_name, svg):
        # type: (AClient, ABlockName, ASvg) -> None
        super(PandAIconPart, self).__init__(svg)
        self.client = client
        self.block_name = block_name

    def update_icon(self, field_values, ts):
        """Update the icon using the given field values"""
