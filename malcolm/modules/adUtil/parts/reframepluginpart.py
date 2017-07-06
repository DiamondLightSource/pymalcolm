from malcolm.core import method_also_takes, method_takes
from malcolm.modules.ADCore.parts import DetectorDriverPart, configure_args
from malcolm.modules.ADCore.infos import NDArrayDatasetInfo
from malcolm.modules.builtin.vmetas import NumberMeta
from malcolm.modules.scanning.controllers import RunnableController


@method_also_takes(
    "sampleFreq", NumberMeta(
        "int32", "Sample frequency of ADC signal in Hz"), 10000)
class ReframePluginPart(DetectorDriverPart):

    @RunnableController.ReportStatus
    def report_configuration(self, context):
        infos = super(ReframePluginPart, self).report_configuration(
            context) + [NDArrayDatasetInfo(rank=2)]
        return infos

    @RunnableController.Validate
    @method_takes(*configure_args)
    def validate(self, context, part_info, params):
        exposure = params.generator.duration
        assert exposure > 0, \
            "Duration %s for generator must be >0 to signify constant exposure"\
            % exposure
        nsamples = int(exposure * self.params.sampleFreq) - 1
        assert nsamples > 0, \
            "Duration %s for generator gives < 1 ADC sample" % exposure

    def setup_detector(self, child, completed_steps, steps_to_do, params=None):
        fs = super(ReframePluginPart, self).setup_detector(
            child, completed_steps, steps_to_do, params)
        nsamples = int(params.generator.duration * self.params.sampleFreq) - 1
        fs.append(child.postCount.put_value_async(nsamples))
        return fs
