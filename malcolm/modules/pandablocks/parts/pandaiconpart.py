from typing import Set

from malcolm.modules import builtin

from ..util import ABlockName, AClient

ASvg = builtin.parts.ASvg


class PandAIconPart(builtin.parts.IconPart):
    update_fields: Set = set()

    def __init__(self, client: AClient, block_name: ABlockName, svg: ASvg) -> None:
        super().__init__(svg)
        self.client = client
        self.block_name = block_name

    def update_icon(self, icon: builtin.util.SVGIcon, field_values: dict) -> None:
        """Update the icon using the given field values"""
