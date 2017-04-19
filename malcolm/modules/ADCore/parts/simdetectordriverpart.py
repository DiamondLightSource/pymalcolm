from malcolm.modules.ADCore.parts import DetectorDriverPart


class SimDetectorDriverPart(DetectorDriverPart):
    def create_attributes(self):
        for data in super(SimDetectorDriverPart, self).create_attributes():
            yield data
        self.trigger_mode.set_value("Software")

