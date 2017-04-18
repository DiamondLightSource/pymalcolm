from malcolm.parts.ADCore.detectordriverpart import DetectorDriverPart


class ExcaliburDriverPart(DetectorDriverPart):
    def post_configure(self, task, params):
        if self.child.triggerMode == "Internal":
            self.trigger_mode.set_value("Software")
        else:
            self.trigger_mode.set_value("Hardware")
        super(ExcaliburDriverPart, self).post_configure(task, params)


