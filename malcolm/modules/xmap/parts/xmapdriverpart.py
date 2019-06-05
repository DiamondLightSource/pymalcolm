from annotypes import add_call_types, Any

from malcolm.modules import ADCore, scanning, builtin


@builtin.util.no_save(
    "collectMode", "pixelAdvanceMode", "presetMode", "ignoreGate",
    "pixelsPerRun", "autoPixelsPerBuffer", "pixelsPerBuffer", "binsInSpectrum",
    "dxp1MaxEnergy", "dxp2MaxEnergy", "dxp3MaxEnergy", "dxp4MaxEnergy",
    "inputLogicPolarity")
class XmapDriverPart(ADCore.parts.DetectorDriverPart):
    """Part for using xmap_driver_block in a scan"""
    # Allow CamelCase as fileDir parameter will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  steps_to_do,  # type: scanning.hooks.AStepsToDo
                  part_info,  # type: scanning.hooks.APartInfo
                  generator,  # type: scanning.hooks.AGenerator
                  fileDir,  # type: scanning.hooks.AFileDir
                  **kwargs  # type: **Any
                  ):
        # type: (...) -> None
        super(XmapDriverPart, self).configure(
            context, completed_steps, steps_to_do, part_info, generator,
            fileDir=fileDir,
            collectMode="MCA mapping",
            pixelAdvanceMode="Gate",
            presetMode="No preset",
            ignoreGate="No",
            pixelsPerRun=steps_to_do,
            autoPixelsPerBuffer="Manual",
            pixelsPerBuffer=1,
            binsInSpectrum=2048,
            dxp1MaxEnergy=4.096,
            dxp2MaxEnergy=4.096,
            dxp3MaxEnergy=4.096,
            dxp4MaxEnergy=4.096,
            inputLogicPolarity="Normal")
