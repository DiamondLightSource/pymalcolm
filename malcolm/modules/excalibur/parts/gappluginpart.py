from malcolm.core import PartRegistrar
from malcolm.modules import builtin, scanning
from ..util import AFillValue


class GapPluginPart(builtin.parts.ChildPart):
    """Gap plugin for setting the fill value"""
    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(GapPluginPart, self).setup(registrar)
        self.register_hooked(scanning.hooks.ConfigureHook, self.configure)
        # Tell the controller to expose some extra configure parameters
        registrar.report(scanning.hooks.ConfigureHook.create_info(
            self.configure))

    def configure(self, context, fill_value=0):
        # type: (scanning.hooks.AContext, AFillValue) -> None
        child = context.block_view(self.mri)
        child.fillValue.put_value(fill_value)
