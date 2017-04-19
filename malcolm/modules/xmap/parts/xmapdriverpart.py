from malcolm.modules.scanning.controllers import RunnableController, \
    configure_args
from malcolm.core import method_takes
from malcolm.modules.ADCore.parts import DetectorDriverPart


class XmapDriverPart(DetectorDriverPart):
    @RunnableController.Configure
    @RunnableController.PostRunReady
    @RunnableController.Seek
    @method_takes(*configure_args)
    def configure(self, context, completed_steps, steps_to_do, part_info,
                  params):
        context.unsubscribe_all()
        child = context.block_view(self.params.mri)
        child.put_attribute_values(dict(
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
            inputLogicPolarity="Normal",
            arrayCounter=completed_steps,
            arrayCallbacks=True))
        self.post_configure(child, params)

