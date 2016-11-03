import os

from malcolm.core import method_takes, REQUIRED
from malcolm.core.vmetas import StringMeta
from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.builtin.runnablechildpart import RunnableChildPart
from malcolm.parts.ADCore.datasettablepart import DatasetProducedInfo


class DatasetRunnableChildPart(RunnableChildPart):

    def update_configure_validate_args(self):
        # Decorate validate and configure with the sum of its parts
        method_metas = [self.child["configure"],
                        DatasetRunnableChildPart.configure.MethodMeta]
        without = ["filePath"]
        self.method_metas["validate"].recreate_from_others(
            method_metas, without)
        self.method_metas["configure"].recreate_from_others(
            method_metas, without)

    # MethodMeta will be filled in at reset()
    @RunnableController.Configure
    @method_takes(
        "fileDir", StringMeta("File dir to write HDF files into"), REQUIRED)
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        file_path = os.path.join(params.fileDir, self.name + ".h5")
        filtered_params = {k: v for k, v in params.items() if k != "fileDir"}
        params = self.child["configure"].prepare_input_map(
            filePath=file_path, **filtered_params)
        task.post(self.child["configure"], params)
        datasets_table = self.child.datasets
        info_list = []
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
