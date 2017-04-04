from malcolm.parts.ADCore.detectordriverpart import DetectorDriverPart


class AndorDriverPart(DetectorDriverPart):
    def post_configure(self, task, params):
        task.put(self.child["acquirePeriod"],
                 self.child.exposure + self.readout_time.value)
        super(AndorDriverPart, self).post_configure(task, params)

