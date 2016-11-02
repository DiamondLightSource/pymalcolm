from malcolm.core import method_takes
from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.builtin.runnablechildpart import RunnableChildPart
from malcolm.parts.ADCore.datasettablepart import DatasetProducedInfo


class DatasetRunnableChildPart(RunnableChildPart):
    # MethodMeta will be filled in by _update_configure_args
    @RunnableController.Configure
    @method_takes()
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        info_list = super(DatasetRunnableChildPart, self).configure(
            completed_steps, steps_to_do, task, part_info, params)
        datasets_table = self.child.datasets
        for i in range(len(datasets_table.name)):
            info = DatasetProducedInfo(
                name=datasets_table.name[i],
                filename=datasets_table.filename[i],
                type=datasets_table.type[i],
                rank=datasets_table.rank[i],
                path=datasets_table.path[i],
                uniqueid=datasets_table.uniqueid[i])
            info_list.append(info)
        return info_list
