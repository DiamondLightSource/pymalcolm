from malcolm.modules.ADCore.parts import ExposureDetectorDriverPart


class AndorDriverPart(ExposureDetectorDriverPart):
    def setup_detector(self, child, completed_steps, steps_to_do, params=None):
        fs = super(AndorDriverPart, self).setup_detector(
            child, completed_steps, steps_to_do, params)
        child.wait_all_futures(fs)
        # Need to reset acquirePeriod as it's sometimes wrong
        fs = child.acquirePeriod.put_value_async(
            child.exposure.value + self.readout_time.value)
        return fs
