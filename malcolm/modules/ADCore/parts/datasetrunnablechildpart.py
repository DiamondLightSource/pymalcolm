from malcolm.core import method_takes
from malcolm.modules.ADCore.infos import DatasetProducedInfo
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.scanning.parts import RunnableChildPart


class DatasetRunnableChildPart(RunnableChildPart):
    """Part controlling a configure/run child Block with a dataset table"""
    def update_part_configure_args(self, response, without=()):
        # Decorate validate and configure with the sum of its parts
        super(DatasetRunnableChildPart, self).update_part_configure_args(
            response, without=without + ("formatName",))

    def _params_with_format_name(self, params):
        new_params = dict(formatName=self.name)
        new_params.update(params)
        return new_params

    # Method will be filled in by update_configure_validate_args
    @RunnableController.Validate
    @method_takes()
    def validate(self, context, part_info, params):
        params = self._params_with_format_name(params)
        return super(DatasetRunnableChildPart, self).validate(
            context, part_info, params)

    # Method will be filled in at update_configure_validate_args
    @RunnableController.Configure
    @method_takes()
    def configure(self, context, completed_steps, steps_to_do, part_info,
                  params):
        child = context.block_view(self.params.mri)
        if "formatName" in child.configure.takes.elements:
            params = self._params_with_format_name(params)
        super(DatasetRunnableChildPart, self).configure(
            context, completed_steps, steps_to_do, part_info, params)
        info_list = []
        if hasattr(child, "datasets"):
            datasets_table = child.datasets.value
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
