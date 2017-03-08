from malcolm.controllers.builtin.runnablecontroller import RunnableController
from malcolm.parts.ADCore.hdfwriterpart import CalculatedNDAttributeDatasetInfo
from malcolm.parts.builtin.childpart import ChildPart


class StatsPluginPart(ChildPart):

    @RunnableController.ReportStatus
    def report_info(self, _):
        return [CalculatedNDAttributeDatasetInfo(name="sum", attr="StatsTotal")]

    @RunnableController.Configure
    def configure(self, task, completed_steps, steps_to_do, part_info):
        task.put_many(self.child, dict(
            enableCallbacks=True,
            computeStatistics=True))
