from malcolm.modules.ADCore.parts \
    import DetectorDriverPart, ExposureDetectorDriverPart
from malcolm.modules.ADCore.infos import NDArrayDatasetInfo
from malcolm.modules.scanning.controllers import RunnableController
from numpy import float64

class Andor3DriverPart(DetectorDriverPart):
    @RunnableController.ReportStatus
    def report_configuration(self, context):
        infos = super(Andor3DriverPart, self).report_configuration(
            context) + [NDArrayDatasetInfo(rank=2)]
        return infos

    def setup_detector(self, child, completed_steps, steps_to_do, params=None):
        fs = super(Andor3DriverPart, self).setup_detector(
            child, completed_steps, steps_to_do, params)

        duration = params.generator.duration
        readout_time = child.readoutTime.value
        exposure = duration - readout_time
        fs.append(child.exposure.put_value_async(exposure))

        child.wait_all_futures(fs)
        # Need to reset acquirePeriod as it's sometimes wrong
        fs = child.acquirePeriod.put_value_async(exposure + readout_time)

        # Logic here:
        #   -   The camera does not set its exposure time to the exact demand
        #       value due to the fact it takes a set amount of time to read
        #       out each row.
        #   -   We cannot calculate this time exactly, it varies depending on
        #       the model and configuration of the detector, but it can be up
        #       to O(0.1ms).
        #   -   The camera automatically sets the acquire period to the
        #       exposure + readout time.
        #   -   If the truncation results in the acquire period being larger
        #       than the duration, duty cycles will overlap. We must ensure
        #       the exposure is set to the demand value or less.
        #   -   If the acquire period is larger than the duration by d, then the
        #       minimum span between possible discrete acquire periods
        #       (and, therefore, exposure times) should be less than 2d.
        #   -   So, if that happens, we subtract 2d from the exposure time.
        #   -   A better solution might be to simply increase the duration value
        #       for the whole scan, based on the acquire period, but we can't
        #       control that from here.
        child.wait_all_futures(fs)
        camera_duty_cycle_overlap = child.acquirePeriod.value - duration
        if camera_duty_cycle_overlap > 0:
            exposure -= camera_duty_cycle_overlap * 2
            fs = child.exposure.put_value_async(exposure)

        # Can't put this in validate as we don't have access to the detector
        # from there, and readout_time comes from a PV.
        assert duration > readout_time, \
            "Given duration %s too small to accommodate camera's " \
            "readoutTime %s" % (
                duration, readout_time)
        return fs
