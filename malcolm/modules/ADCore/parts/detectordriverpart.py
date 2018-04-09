from annotypes import Anno, add_call_types, Any

from malcolm.core import APartName, BadValueError
from malcolm.modules.builtin.parts import AMri, ChildPart
from malcolm.modules.scanning.hooks import ReportStatusHook, \
    ConfigureHook, PostRunArmedHook, SeekHook, RunHook, ResumeHook, PauseHook, \
    AbortHook, AContext, UInfos, AStepsToDo, ACompletedSteps, APartInfo
from malcolm.modules.scanning.util import AGenerator
from ..infos import NDArrayDatasetInfo, ExposureDeadtimeInfo
from ..util import ADBaseActions

with Anno("Is detector hardware triggered?"):
    AHardwareTriggered = bool
with Anno("Is main detector dataset useful to publish in DatasetTable?"):
    AMainDatasetUseful = bool


class DetectorDriverPart(ChildPart):
    def __init__(self,
                 name,  # type: APartName
                 mri,  # type: AMri
                 is_hardware_triggered=True,  # type: AHardwareTriggered
                 main_dataset_useful=True,  # type: AMainDatasetUseful
                 ):
        # type: (...) -> None
        super(DetectorDriverPart, self).__init__(name, mri)
        self.is_hardware_triggered = is_hardware_triggered
        self.main_dataset_useful = main_dataset_useful
        self.actions = ADBaseActions(mri)
        # Hooks
        self.register_hooked(ReportStatusHook, self.report_status)
        self.register_hooked((ConfigureHook, PostRunArmedHook, SeekHook),
                             self.configure)
        self.register_hooked((RunHook, ResumeHook), self.run)
        self.register_hooked((PauseHook, AbortHook), self.abort)

    @add_call_types
    def reset(self, context):
        # type: (AContext) -> None
        super(DetectorDriverPart, self).reset(context)
        self.actions.abort_detector(context)

    @add_call_types
    def report_status(self):
        # type: () -> UInfos
        if self.main_dataset_useful:
            return NDArrayDatasetInfo(rank=2)

    @add_call_types
    def configure(self,
                  context,  # type: AContext
                  completed_steps,  # type: ACompletedSteps
                  steps_to_do,  # type: AStepsToDo
                  part_info,  # type: APartInfo
                  generator,  # type: AGenerator
                  **kwargs  # type: **Any
                  ):
        # type: (...) -> None
        try:
            exposure_info = ExposureDeadtimeInfo.filter_single_value(part_info)
        except BadValueError:
            # This is allowed, no exposure required
            pass
        else:
            kwargs["exposure"] = exposure_info.calculate_exposure(
                generator.duration)
        self.actions.setup_detector(
            context, completed_steps, steps_to_do, **kwargs)
        if self.is_hardware_triggered:
            # Start now if we are hardware triggered
            self.actions.arm_detector(context)

    @add_call_types
    def run(self, context):
        # type: (AContext) -> None
        if not self.is_hardware_triggered:
            # Start now if we are software triggered
            self.actions.arm_detector(context)
        self.actions.wait_for_detector(context, self.registrar)

    @add_call_types
    def abort(self, context):
        # type: (AContext) -> None
        self.actions.abort_detector(context)
