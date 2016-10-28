from malcolm.parts.builtin.childpart import ChildPart
from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.ADCore.hdfwriterpart import DatasetSourceInfo


class StatsPluginPart(ChildPart):

    @RunnableController.ReportStatus
    def report_info(self, _):
        return [DatasetSourceInfo("StatsTotal", "additional")]

    @RunnableController.Configure
    def configure(self, task, completed_steps, steps_to_do, part_info):
        task.put_many(self.child, dict(
            enableCallbacks=True,
            computeStatistics=True))
