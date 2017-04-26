from malcolm.modules.ADCore.parts import ExposureDetectorDriverPart


class ExcaliburDriverPart(ExposureDetectorDriverPart):
    def post_configure(self, context, params):
        child = context.block_view(self.params.mri)
        if child.triggerMode.value == "Internal":
            self.trigger_mode.set_value("Software")
        else:
            self.trigger_mode.set_value("Hardware")
        super(ExcaliburDriverPart, self).post_configure(context, params)


