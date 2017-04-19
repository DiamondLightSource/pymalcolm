from malcolm.modules.builtin.controllers import ManagerController
from .childpart import ChildPart


ss = ManagerController.stateSet


class StatefulChildPart(ChildPart):
    @ManagerController.Init
    def init(self, context):
        # Wait for a while until the child is ready as it changes the save state
        context.when_matches(
            [self.params.mri, "state", "value"], ss.READY,
            [ss.FAULT, ss.DISABLED])
        super(StatefulChildPart, self).init(context)

    @ManagerController.Disable
    def disable(self, context):
        child = context.block_view(self.params.mri)
        if child.disable.writeable:
            child.disable()

    @ManagerController.Reset
    def reset(self, context):
        child = context.block_view(self.params.mri)
        if child.reset.writeable:
            child.reset()
