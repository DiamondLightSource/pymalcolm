import os

from malcolm.modules import builtin
from malcolm.core import StringMeta, PartRegistrar
from malcolm.modules import ca
from .dirparsepart import AIoc


class IocIconPart(builtin.parts.IconPart):
    def __init__(self, ioc, initial_svg):
        # type: (AIoc, builtin.parts.ASvg) -> None
        self.initial_svg = initial_svg
        super(IocIconPart, self).__init__(initial_svg)
        self.host_arch = ca.util.CAAttribute(
            StringMeta("Host Architecture"), ca.util.catools.DBR_STRING,
            "", ioc + ":KERNEL_VERS", throw=False, callback=self.update_icon)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(IocIconPart, self).setup(registrar)
        self.host_arch.setup(registrar, "hostOs", self.register_hooked)

    def update_icon(self, arch):
        svg = self.initial_svg
        if arch.ok:
            if arch.startswith("WIND"):
                svg = os.path.split(__file__)[0] + "/../icons/vx_epics.svg"
            elif arch.startswith("Linux"):
                svg = os.path.split(__file__)[0] + "/../icons/linux_epics.svg"
            elif arch.startswith("Windows"):
                svg = os.path.split(__file__)[0] + "/../icons/win_epics.svg"
            else:
                svg = os.path.split(__file__)[0] + "/../icons/epics-logo.svg"
        with open(svg) as f:
            svg_text = f.read()
            self.attr.set_value(svg_text)
