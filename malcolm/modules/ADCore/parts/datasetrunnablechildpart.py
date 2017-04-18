import os

from malcolm.controllers.scanning.runnablecontroller import RunnableController
from malcolm.core import method_takes, REQUIRED, Update, \
    MethodModel, deserialize_object
from malcolm.infos.ADCore.datasetproducedinfo import DatasetProducedInfo
from malcolm.parts.scanning.runnablechildpart import RunnableChildPart
from malcolm.modules.builtin.vmetas import StringMeta


class DatasetRunnableChildPart(RunnableChildPart):
    def update_configure_args(self, response):
        # Decorate validate and configure with the sum of its parts
        response = deserialize_object(response, Update)
        method_metas = [deserialize_object(response.value, MethodModel),
                        DatasetRunnableChildPart.configure.MethodModel]
        without = ["filePath"]
        self.method_models["validate"].recreate_from_others(
            method_metas, without)
        self.method_models["configure"].recreate_from_others(
            method_metas, without)
        self.controller.update_configure_args()

    def _params_with_file_path(self, params):
        file_path = os.path.join(params.fileDir, self.name + ".h5")
        filtered_params = {k: v for k, v in params.items() if k != "fileDir"}
        filtered_params["filePath"] = file_path
        return filtered_params

    # Method will be filled in by update_configure_validate_args
    @RunnableController.Validate
    @method_takes()
    def validate(self, context, part_info, params):
        params = self._params_with_file_path(params)
        return super(DatasetRunnableChildPart, self).validate(
            context, part_info, params)

    # Method will be filled in at update_configure_validate_args
    @RunnableController.Configure
    @method_takes(
        "fileDir", StringMeta("File dir to write HDF files into"), REQUIRED)
    def configure(self, context, completed_steps, steps_to_do, part_info,
                  params):
        child = context.block_view(self.params.mri)
        if "filePath" in child.configure.takes.elements:
            params = self._params_with_file_path(params)
        child.configure(**params)
        datasets_table = child.datasets.value
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
