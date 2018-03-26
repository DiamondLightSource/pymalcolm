from malcolm.core import method_takes, REQUIRED
from malcolm.modules.builtin.vmetas import StringMeta
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.ADCore.parts import DatasetRunnableChildPart


class FemChildPart(DatasetRunnableChildPart):

    # MethodMeta will be filled in at reset()
    @RunnableController.Configure
    @method_takes(
        "fileDir", StringMeta("File dir to write HDF files into"), REQUIRED)
    def configure(self, context, completed_steps, steps_to_do, part_info,
                  params):
        # Throw away the dataset info the superclass returns
        super(FemChildPart, self).configure(
            context, completed_steps, steps_to_do, part_info, params)
        # Sleep after configuration - recommended to allow at least 1s after starting Excalibur before taking first frame
        # following testing on J13. Otherwise FEM1 may not be ready and will drop a frame.
        print("Sleeping...")
        context.sleep(1.0)
        print("Slept")
