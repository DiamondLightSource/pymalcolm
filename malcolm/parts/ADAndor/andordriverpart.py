from malcolm.core import method_takes, REQUIRED
from malcolm.core.vmetas import PointGeneratorMeta
from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.ADCore.detectordriverpart import DetectorDriverPart


class AndorDriverPart(DetectorDriverPart):
    def post_configure(self, task, params):
        task.put(self.child["acquirePeriod"], self.child.exposure + self.readout_time.value)
        super(AndorDriverPart, self).post_configure(task, params)

