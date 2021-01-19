import cothread
from annotypes import Anno, add_call_types

from malcolm.modules import scanning

from .hdfwriterpart import (
    AMri,
    APartName,
    APartRunsOnWindows,
    AWriteAllNDAttributes,
    HDFWriterPart,
)

with Anno("Approximate timeout before stopping writer"):
    AWriterTimeout = float


class HDFContinuousWriterPart(HDFWriterPart):
    """Writer part which keeps running forever"""

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def on_configure(
        self,
        context: scanning.hooks.AContext,
        completed_steps: scanning.hooks.ACompletedSteps,
        steps_to_do: scanning.hooks.AStepsToDo,
        part_info: scanning.hooks.APartInfo,
        generator: scanning.hooks.AGenerator,
        fileDir: scanning.hooks.AFileDir,
        formatName: scanning.hooks.AFormatName = "det",
        fileTemplate: scanning.hooks.AFileTemplate = "%s.h5",
    ) -> scanning.hooks.UInfos:

        dataset_infos = super().on_configure(
            context,
            completed_steps,
            steps_to_do,
            part_info,
            generator,
            fileDir,
            formatName,
            fileTemplate,
        )

        # Turn position mode off as these do not correspond to when our data arrives
        child = context.block_view(self.mri)
        child.positionMode.put_value(False)

        return dataset_infos

    @add_call_types
    def on_run(self, context: scanning.hooks.AContext) -> None:
        pass
