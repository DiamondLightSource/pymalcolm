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


class HDFWriterWithTimeoutPart(HDFWriterPart):
    """Writer part which keeps running until frames stop arriving based on a timeout"""

    def __init__(
        self,
        name: APartName,
        mri: AMri,
        timeout: AWriterTimeout,
        runs_on_windows: APartRunsOnWindows = False,
        write_all_nd_attributes: AWriteAllNDAttributes = True,
    ) -> None:
        super().__init__(
            name,
            mri,
            runs_on_windows=runs_on_windows,
            write_all_nd_attributes=write_all_nd_attributes,
        )
        self.timeout = timeout
        self.queue_poll = 0.1

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
        context.wait_all_futures(self.array_future)
        context.unsubscribe_all()
        self.last_id_update = None
        child = context.block_view(self.mri)
        child.uniqueId.subscribe_value(self.update_completed_steps)

        # Wait for uniqueIds to stop increasing
        last_unique_id = child.uniqueId.value
        cothread.Sleep(1.5 * self.timeout)
        current_unique_id = child.uniqueId.value
        while current_unique_id != last_unique_id:
            last_unique_id = current_unique_id
            cothread.Sleep(1.5 * self.timeout)
            current_unique_id = child.uniqueId.value

        # Check queue and try flushing
        while child.queueUse.value > 0:
            cothread.Sleep(self.queue_poll)
            child.flushNow()
