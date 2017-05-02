from malcolm.modules.ADCore.parts import ExposureDetectorDriverPart


class SimDetectorDriverPart(ExposureDetectorDriverPart):
    def is_hardware_triggered(self, child):
        return False

