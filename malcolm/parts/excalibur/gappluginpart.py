from malcolm.core import method_takes
from malcolm.core.vmetas import NumberMeta
from malcolm.parts.builtin.childpart import ChildPart
from malcolm.controllers.runnablecontroller import RunnableController


class GapPluginPart(ChildPart):
    """Gap plugin"""

    fill_value = 0

    @RunnableController.Configure
    @method_takes(
        "fillValue", NumberMeta("int32", "Fill value for stripe spacing"), 0)
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        self.fill_value = params.fillValue
        fs = task.put_async(self.child["fillValue"], self.fill_value)
        task.wait_all(fs)
