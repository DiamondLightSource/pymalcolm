from malcolm.modules.builtin.parts import StatefulChildPart
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.ADCore.infos import NDArrayDatasetInfo


class FemDriverPart(StatefulChildPart):
    # Only need to report that we will make a dataset, top level will do all
    # control
    @RunnableController.ReportStatus
    def report_configuration(self, _):
        return [NDArrayDatasetInfo(name=self.name, rank=2)]
