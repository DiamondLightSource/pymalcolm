from malcolm.core import method_also_takes, REQUIRED, method_takes
from malcolm.modules.ADCore.infos import NDArrayDatasetInfo
from malcolm.modules.builtin.vmetas import NumberMeta
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.scanpointgenerator.vmetas import PointGeneratorMeta
from malcolm.tags import widget, config
from .detectordriverpart import DetectorDriverPart

# Args for configure() and validate
configure_args = [
    "generator", PointGeneratorMeta("Generator instance"), REQUIRED]


@method_also_takes(
    "readoutTime", NumberMeta(
        "float64", "Default time taken to readout detector"), 7e-5)
class ExposureDetectorDriverPart(DetectorDriverPart):
    # Attributes
    readout_time = None

    def create_attributes(self):
        for data in super(ExposureDetectorDriverPart, self).create_attributes():
            yield data
        # Create writeable attribute for how long we should allow for detector
        # read out
        meta = NumberMeta(
            "float64", "Time taken to readout detector",
            tags=[widget("textinput"), config()])
        self.readout_time = meta.create_attribute(self.params.readoutTime)
        yield "readoutTime", self.readout_time, self.readout_time.set_value

    @RunnableController.ReportStatus
    def report_configuration(self, context):
        infos = super(ExposureDetectorDriverPart, self).report_configuration(
            context) + [NDArrayDatasetInfo(rank=2)]
        return infos

    @RunnableController.Validate
    @method_takes(*configure_args)
    def validate(self, context, part_info, params):
        exposure = params.generator.duration
        assert exposure > 0, \
            "Duration %s for generator must be >0 to signify constant exposure"\
            % exposure
        # TODO: should really get this from an Info from pmac trajectory part...
        exposure -= self.readout_time.value
        assert exposure > 0.0, \
            "Exposure time %s too small when readoutTime taken into account" % (
                exposure)

    @RunnableController.Configure
    @RunnableController.PostRunReady
    @RunnableController.Seek
    @method_takes(*configure_args)
    def configure(self, context, completed_steps, steps_to_do, part_info,
                  params=None):
        return super(ExposureDetectorDriverPart, self).configure(
            context, completed_steps, steps_to_do, part_info, params)

    def setup_detector(self, child, completed_steps, steps_to_do, params=None):
        fs = super(ExposureDetectorDriverPart, self).setup_detector(
            child, completed_steps, steps_to_do, params)
        exposure = params.generator.duration - self.readout_time.value
        fs.append(child.exposure.put_value_async(exposure))
        return fs
