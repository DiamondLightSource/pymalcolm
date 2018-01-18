from malcolm.modules.builtin.parts import ChildPart
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.ADCore.infos import NDArrayDatasetInfo, UniqueIdInfo


class FemDriverPart(ChildPart):
    # Only need to report that we will make a dataset, top level will do all
    # control
    @RunnableController.ReportStatus
    def report_configuration(self, context):
        child = context.block_view(self.params.mri)
        return [
            NDArrayDatasetInfo(rank=2), UniqueIdInfo(child.arrayCounter.value)]
