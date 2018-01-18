from malcolm.core import method_takes
from malcolm.modules.builtin.parts import ChildPart
from malcolm.core.vmetas import NumberMeta
from malcolm.modules.scanning.controllers import RunnableController


class GapPluginPart(ChildPart):
    """Gap plugin for setting the fill value"""
    @RunnableController.Configure
    @method_takes(
        "fillValue", NumberMeta("int32", "Fill value for stripe spacing"), 0)
    def configure(self, context, completed_steps, steps_to_do, part_info,
                  params):
        child = context.block_view(self.params.mri)
        child.fillValue.put_value(params.fillValue)
