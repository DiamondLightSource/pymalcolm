import numpy as np

from malcolm.modules.ADCore.parts import DetectorDriverPart
from malcolm.modules.ADCore.infos import NDArrayDatasetInfo
from malcolm.modules.scanning.controllers import RunnableController


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

        # TODO: Should have separate validate method that can access
        # readout time
        assert duration >= readout_time, \
            "Cannot expose detector in given duration, %f because its " \
            "readout time %f is too large" % (duration, readout_time)

        # On the detector, the exposure time can only be set to a multiple of
        # row_readout_time, the time taken to read out a row of pixels.
        # Use of the floor function ensures that exposure time is set to the
        # largest possible value under the target. The readout time is
        # subtracted because the camera has additional dead time that is given
        # in "rows" in the Andor Neo hardware guide (page 57).
        #
        # Note: row_readout_time can only be calculated like this when the
        # camera is not in overlap mode
        row_readout_time = readout_time / child.arrayHeight.value
        ideal_exposure = duration - readout_time
        extra_rows = {
            "Rolling": 1,
            "Global": 4
        }[child.shutterMode.value]
        exposure = \
            (np.floor(ideal_exposure / row_readout_time) - extra_rows) \
            * row_readout_time

        fs.append(child.exposure.put_value_async(exposure))

        # Need to reset acquirePeriod after setting exposure as it's
        # sometimes wrong
        child.wait_all_futures(fs)
        fs = child.acquirePeriod.put_value_async(exposure + readout_time)

        return fs
