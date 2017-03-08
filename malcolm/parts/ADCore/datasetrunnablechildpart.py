import os

from malcolm.controllers.builtin.runnablecontroller import RunnableController
from malcolm.core import method_takes, REQUIRED
from malcolm.parts.ADCore.datasettablepart import DatasetProducedInfo
from malcolm.parts.builtin.runnablechildpart import RunnableChildPart
from malcolm.vmetas.builtin import StringMeta


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

    def _params_with_file_path(self, params):
        file_path = os.path.join(params.fileDir, self.name + ".h5")
        filtered_params = {k: v for k, v in params.items() if k != "fileDir"}
        params = self.child["configure"].prepare_input_map(
            filePath=file_path, **filtered_params)
        return params

    # Method will be filled in by _update_configure_args
    @RunnableController.Validate
    @method_takes()
    def validate(self, task, part_info, params):
        params = self._params_with_file_path(params)
        return super(DatasetRunnableChildPart, self).validate(
            task, part_info, params)

    # Method will be filled in at reset()
    @RunnableController.Configure
    @method_takes(
        "fileDir", StringMeta("File dir to write HDF files into"), REQUIRED)
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        params = self._params_with_file_path(params)
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
