import time

from malcolm.core import Attribute, Controller, method_takes, REQUIRED, \
    RunnableDeviceStateMachine
from malcolm.core.vmetas import NumberMeta, PointGeneratorMeta, StringMeta


@RunnableDeviceStateMachine.insert
@method_takes()
class ScanPointTickerController(Controller):
    # The Attributes we will create
    value = None
    generator = None
    axis_name = None
    exposure = None

    def create_attributes(self):
        self.value = Attribute(NumberMeta("float64", "Value"))
        yield 'value', self.value, None
        self.generator = Attribute(PointGeneratorMeta("Scan Point Generator"))
        yield "generator", self.generator, None
        self.axis_name = Attribute(StringMeta("Name of the axis"))
        yield "axis_name", self.axis_name, None
        self.exposure = Attribute(NumberMeta("float64", "Exposure time"))
        yield "exposure", self.exposure, None

    @method_takes(
        "generator", PointGeneratorMeta("Generator instance"), REQUIRED,
        "axis_name", StringMeta("Specifier for axis"), REQUIRED,
        "exposure", NumberMeta("int32", "Detector exposure time"), REQUIRED)
    def configure(self, params):
        """
        Configure the controller with params
        """
        self.generator.set_value(params.generator)
        self.axis_name.set_value(params.axis_name)
        self.exposure.set_value(params.exposure)

    @method_takes()
    def run(self):
        """
        Start the ticker process
        """
        axis_name = self.axis_name.value
        for point in self.generator.value.iterator():
            self.value.set_value(point.positions[axis_name])
            time.sleep(self.exposure.value)
