from malcolm.modules.ADCore.parts import ExposureDetectorDriverPart


class SimDetectorDriverPart(ExposureDetectorDriverPart):
    """Part for controlling a `sim_detector_driver_block` in a Device"""

    def is_hardware_triggered(self, child):
        return False

