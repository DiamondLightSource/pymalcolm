from malcolm.modules.ADCore.parts import ExposureDetectorDriverPart


XSPRESS3_BUFFER = 16384


class Xspress3DriverPart(ExposureDetectorDriverPart):
    def setup_detector(self, child, completed_steps, steps_to_do, params=None):
        if steps_to_do > XSPRESS3_BUFFER:
            # Set the PointsPerRow from the innermost dimension
            gen_num = params.generator.dimensions[-1].size
            steps_per_row = XSPRESS3_BUFFER // gen_num * gen_num
        else:
            steps_per_row = steps_to_do
        fs = child.put_attribute_values_async(dict(
            pointsPerRow=steps_per_row,
            # TODO: this goes in config
            triggerMode="Hardware"))
        fs += super(Xspress3DriverPart, self).setup_detector(
            child, completed_steps, steps_to_do, params)
        return fs
