from malcolm.modules.ADCore.parts import DetectorDriverPart


class XmapDriverPart(DetectorDriverPart):
    # No numImages or imageMode so no superclass call
    def setup_detector(self, child, completed_steps, steps_to_do, params=None):
        fs = child.put_attribute_values_async(dict(
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
        return fs
