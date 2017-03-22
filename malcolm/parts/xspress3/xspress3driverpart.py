from malcolm.core import method_takes, REQUIRED
from malcolm.core.vmetas import PointGeneratorMeta
from malcolm.controllers.runnablecontroller import RunnableController, configure_args
from malcolm.parts.ADCore.detectordriverpart import DetectorDriverPart


XSPRESS3_BUFFER = 16384


class Xspress3DriverPart(DetectorDriverPart):
    @RunnableController.Configure
    @RunnableController.PostRunReady
    @RunnableController.Seek
    @method_takes(*configure_args)
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        if steps_to_do > XSPRESS3_BUFFER:
            # Set the PointsPerRow from the innermost dimension
            gen_num = params.generator.dimensions[-1].size
            steps_per_row = XSPRESS3_BUFFER // gen_num * gen_num
        else:
            steps_per_row = steps_to_do
        task.put(self.child["pointsPerRow"], steps_per_row)
        super(Xspress3DriverPart, self).configure(
            task, completed_steps, steps_to_do, part_info, params)
