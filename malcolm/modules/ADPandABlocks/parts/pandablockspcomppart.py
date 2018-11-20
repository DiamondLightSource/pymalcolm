from annotypes import add_call_types

from malcolm.core import APartName
from malcolm.modules import builtin, scanning


class PandABlocksPcompPart(builtin.parts.ChildPart):
    """Part for controlling a `stats_plugin_block` in a Device"""

    def __init__(self, name, mri):
        # type: (APartName, builtin.parts.AMri) -> None
        super(PandABlocksPcompPart, self).__init__(name, mri)
        # Stored generator for positions
        self.generator = None
        # The last index we have loaded
        self.loaded_up_to = 0
        # The last scan point index of the current run
        self.scan_up_to = 0
        # If we are currently loading then block loading more points
        self.loading = False
        # The mri of the panda we should be prodding
        self.panda_mri = None
        # Hooks
        self.register_hooked(scanning.hooks.ConfigureHook,
                             self.configure)
        self.register_hooked(scanning.hooks.PostConfigureHook,
                             self.post_configure)
        self.register_hooked(scanning.hooks.RunHook,
                             self.run)

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  steps_to_do,  # type: scanning.hooks.AStepsToDo
                  part_info,  # type: scanning.hooks.APartInfo
                  generator,  # type: scanning.hooks.AGenerator
                  axesToMove  # type: scanning.hooks.AAxesToMove
                  ):
        # type: (...) -> None
        self.generator = generator
        self.loaded_up_to = completed_steps
        self.scan_up_to = completed_steps + steps_to_do
        # TODO: check for motor info and store
        assert part_info
        # TODO: store here?
        assert axesToMove
        self.panda_mri = context.block_view(self.mri).panda.value

    @add_call_types
    def post_configure(self, context):
        # type: (scanning.hooks.AContext) -> None
        # load up the first SEQ
        panda = context.block_view(self.panda_mri)
        panda.seqTableA.put_value({})

    @add_call_types
    def run(self, context):
        # type: (scanning.hooks.AContext) -> None
        panda = context.block_view(self.panda_mri)
        panda.seqTableB.put_value({})
