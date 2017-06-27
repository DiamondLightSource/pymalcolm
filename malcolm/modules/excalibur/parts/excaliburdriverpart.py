from malcolm.modules.ADCore.parts import ExposureDetectorDriverPart


class ExcaliburDriverPart(ExposureDetectorDriverPart):
    def is_hardware_triggered(self, child):
        return child.triggerMode.value != "Internal"


