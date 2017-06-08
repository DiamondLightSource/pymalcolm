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
        without = ["formatName"]
        self.method_metas["validate"].recreate_from_others(
            method_metas, without)
        self.method_metas["configure"].recreate_from_others(
            method_metas, without)

    def _params_with_format_name(self, params):
        params = self.child["configure"].prepare_input_map(
            formatName=self.name, **params)
        return params

    # MethodMeta will be filled in by _update_configure_args
    @RunnableController.Validate
    @method_takes()
    def validate(self, task, part_info, params):
        params = self._params_with_format_name(params)
        return super(DatasetRunnableChildPart, self).validate(
            task, part_info, params)

    # MethodMeta will be filled in at reset()
    @RunnableController.Configure
    @method_takes()
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        if "formatName" in self.child["configure"].takes.elements:
            params = self._params_with_format_name(params)
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
