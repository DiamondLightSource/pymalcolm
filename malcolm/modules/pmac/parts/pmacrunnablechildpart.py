from annotypes import add_call_types

from malcolm.core import PartRegistrar
from malcolm.modules import scanning


class PmacRunnableChildPart(scanning.parts.RunnableChildPart):
    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(PmacRunnableChildPart, self).setup(registrar)
        self.register_hooked(scanning.hooks.PauseHook, self.pause)

    # TODO: not sure if this is still needed to reset triggers on pause?
    # Think it probably is because we need to reset triggers before rearming
    # detectors
    @add_call_types
    def pause(self, context):
        # type: (scanning.hooks.AContext) -> None
        child = context.block_view(self.mri)
        child.pause()
