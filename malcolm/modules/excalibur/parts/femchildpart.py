from malcolm.core import method_takes, REQUIRED
from malcolm.core.vmetas import StringMeta
from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.ADCore.datasetrunnablechildpart import \
    DatasetRunnableChildPart


class FemChildPart(DatasetRunnableChildPart):

    # MethodMeta will be filled in at reset()
    @RunnableController.Configure
    @method_takes(
        "fileDir", StringMeta("File dir to write HDF files into"), REQUIRED)
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        # Throw away the dataset info the superclass returns
        super(FemChildPart, self).configure(
            task, completed_steps, steps_to_do, part_info, params)
