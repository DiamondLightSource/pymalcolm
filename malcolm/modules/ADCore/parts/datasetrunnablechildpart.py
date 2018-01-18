from malcolm.core import Part, PartRegistrar, Hook
from malcolm.modules.ADCore.infos import DatasetProducedInfo
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.scanning.hooks import ValidateHook, ConfigureHook
from malcolm.modules.scanning.parts.runnablechildpart import \
    RunnableChildPart, APartName, AMri


class DatasetRunnableChildPart(Part):
    """Part controlling a configure/run child Block with a dataset table"""

    def __init__(self, name, mri):
        # type: (APartName, AMri) -> None
        super(DatasetRunnableChildPart, self).__init__(name)
        self.rcp = RunnableChildPart(
            name, mri, ignore_configure_args=["formatName"])

    def _params_with_format_name(self, params):
        # type: (ConfigureParams)
        new_params = dict(formatName=self.name)
        new_params.update(params)
        return new_params

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.rcp.setup(registrar)

    def on_hook(self, hook):
        # type: (Hook) -> None
        if isinstance(hook, ValidateHook):
            hook.run(self.validate)

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
