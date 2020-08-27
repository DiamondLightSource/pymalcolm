from malcolm.core import Context
from malcolm.modules import builtin, scanning
from malcolm.modules.ADCore.parts import DetectorDriverPart

from annotypes import add_call_types, Any

# We will set these attributes on the child block, so don't save them
@builtin.util.no_save('arrayCounter', 'imageMode', 'numImages',
                      'arrayCallbacks', 'exposure', 'acquirePeriod')
class OdinDriverPart(DetectorDriverPart):
    def setup_detector(self,
                   context,  # type: Context
                   completed_steps,  # type: scanning.hooks.ACompletedSteps
                   steps_to_do,  # type: scanning.hooks.AStepsToDo
                   duration,  # type: float
                   part_info,  # type: scanning.hooks.APartInfo
                   **kwargs  # type: Any
                   ):
        # type: (...) -> None
        super(OdinDriverPart, self).setup_detector(context, 0, steps_to_do, duration, part_info)

    @add_call_types
    def on_reset(self, context):
        # type: (scanning.hooks.AContext) -> None
        super(OdinDriverPart, self).on_reset(context)

    @add_call_types
    def on_report_status(self):
        # type: () -> scanning.hooks.UInfos
        super(OdinDriverPart, self).on_report_status()

    # Allow CamelCase as fileDir parameter will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def on_configure(self,
                     context,  # type: scanning.hooks.AContext
                     completed_steps,  # type: scanning.hooks.ACompletedSteps
                     steps_to_do,  # type: scanning.hooks.AStepsToDo
                     part_info,  # type: scanning.hooks.APartInfo
                     generator,  # type: scanning.hooks.AGenerator
                     fileDir,  # type: scanning.hooks.AFileDir
                     **kwargs  # type: Any
                     ):
        # type: (...) -> None
        super(OdinDriverPart, self).on_configure(context, completed_steps, steps_to_do, part_info, generator, fileDir, **kwargs)

    @add_call_types
    def on_run(self, context):
        # type: (scanning.hooks.AContext) -> None
        super(OdinDriverPart, self).on_run(context)

    @add_call_types
    def on_abort(self, context):
        # type: (scanning.hooks.AContext) -> None
        self.abort_detector(context)
