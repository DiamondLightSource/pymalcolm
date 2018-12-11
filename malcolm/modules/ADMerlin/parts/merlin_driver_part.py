from annotypes import add_call_types, Any, Anno
from malcolm.modules.scanning.hooks import AContext, AStepsToDo, ACompletedSteps, APartInfo
from malcolm.modules.scanning.util import AGenerator
from malcolm.core import APartName, BadValueError
from malcolm.modules.builtin.parts import AMri

from malcolm.modules.ADCore.parts import DetectorDriverPart, AHardwareTriggered, AMainDatasetUseful
from malcolm.modules.ADCore.infos import ExposureDeadtimeInfo

with Anno("Fudge factor to deal with missing triggers if acquisition period is too close to generator duration"):
    AFudgeFactor = float

class MerlinDriverPart(DetectorDriverPart):
    def __init__(self,
                 name,                          # type: APartName
                 mri,                           # type: AMri
                 is_hardware_triggered=True,    # type: AHardwareTriggered
                 main_dataset_useful=True,      # type: AMainDatasetUseful
                 fudge_factor=0.0               # type: AFudgeFactor
                 ):
        # type: (...) -> None
        super(MerlinDriverPart, self).__init__(name, mri, is_hardware_triggered, main_dataset_useful)
        self.fudge_factor = fudge_factor

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
            exposure_info = None
        else:
            kwargs["exposure"] = exposure_info.calculate_exposure(
                generator.duration-self.fudge_factor)
        self.actions.setup_detector(
            context, completed_steps, steps_to_do, **kwargs)
        # Might need to reset acquirePeriod as it's sometimes wrong
        # in some detectors
        if exposure_info:
            child = context.block_view(self.mri)
            child.acquirePeriod.put_value(generator.duration-self.fudge_factor)
        if self.is_hardware_triggered:
            # Start now if we are hardware triggered
            self.actions.arm_detector(context)
