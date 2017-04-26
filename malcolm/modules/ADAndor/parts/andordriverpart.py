from malcolm.modules.ADCore.parts import ExposureDetectorDriverPart


class AndorDriverPart(ExposureDetectorDriverPart):
    def post_configure(self, context, params):
        child = context.block_view(self.params.mri)
        child.acquirePeriod.put_value(
            child.exposure.value + self.readout_time.value)
        super(AndorDriverPart, self).post_configure(context, params)
