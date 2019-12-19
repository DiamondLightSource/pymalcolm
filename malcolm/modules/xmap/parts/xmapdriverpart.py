from annotypes import Any

from malcolm.core import Context
from malcolm.modules import ADCore, scanning, builtin


@builtin.util.no_save(
    "collectMode", "pixelAdvanceMode", "presetMode", "ignoreGate",
    "pixelsPerRun", "autoPixelsPerBuffer", "pixelsPerBuffer", "binsInSpectrum",
    "inputLogicPolarity")
class XmapDriverPart(ADCore.parts.DetectorDriverPart):
    """Part for using xmap_driver_block in a scan"""
    def setup_detector(self,
                       context,  # type: Context
                       completed_steps,  # type: scanning.hooks.ACompletedSteps
                       steps_to_do,  # type: scanning.hooks.AStepsToDo
                       duration,  # type: int
                       part_info,  # type: scanning.hooks.APartInfo
                       **kwargs  # type: Any
                       ):
        # type: (...) -> None
        super(XmapDriverPart, self).setup_detector(
            context, completed_steps, steps_to_do, duration, part_info,
            collectMode="MCA mapping",
            pixelAdvanceMode="Gate",
            presetMode="No preset",
            ignoreGate="No",
            pixelsPerRun=steps_to_do,
            autoPixelsPerBuffer="Manual",
            pixelsPerBuffer=1,
            binsInSpectrum=2048,
            inputLogicPolarity="Normal",
            **kwargs
        )
