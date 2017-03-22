from malcolm.controllers.builtin import ManagerController
from .childpart import ChildPart


class StatefulChildPart(ChildPart):
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
