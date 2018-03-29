from malcolm.modules import scanning, builtin, ADCore


class FemDriverPart(builtin.parts.ChildPart):
    def setup(self, registrar):
        super(FemDriverPart, self).setup(registrar)
        # Hooks
        self.register_hooked(scanning.hooks.ReportStatusHook,
                             self.report_status)

    # Only need to report that we will make a dataset, top level will do all
    # control
    def report_status(self):
        # type: () -> scanning.hooks.UInfos
        return ADCore.infos.NDArrayDatasetInfo(rank=2)
