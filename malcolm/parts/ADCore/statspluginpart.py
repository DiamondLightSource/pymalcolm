from malcolm.parts.builtin.layoutpart import LayoutPart
from malcolm.controllers.runnablecontroller import RunnableController


class StatsPluginPart(LayoutPart):
    @RunnableController.Configuring
    def configure(self, task, completed_steps, steps_to_do, part_info):
        task.put({
            self.child["enableCallbacks"]: True,
            self.child["computeStatistics"]: True,
        })
