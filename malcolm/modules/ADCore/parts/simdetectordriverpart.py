from malcolm.modules.ADCore.parts import ExposureDetectorDriverPart


class SimDetectorDriverPart(ExposureDetectorDriverPart):
    def create_attributes(self):
        for data in super(SimDetectorDriverPart, self).create_attributes():
            yield data
        self.trigger_mode.set_value("Software")

