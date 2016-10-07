from malcolm.parts.builtin.layoutpart import LayoutPart
from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.ADCore.hdfwriterpart import DatasetInfo

class StatsPluginPart(LayoutPart):

    @RunnableController.Report
    def report_info(self, _):
        return [DatasetInfo("StatsTotal", "additional")]

    @RunnableController.Configuring
    def configure(self, task, completed_steps, steps_to_do, part_info):
        task.put({
            self.child["enableCallbacks"]: True,
            self.child["computeStatistics"]: True,
        })
