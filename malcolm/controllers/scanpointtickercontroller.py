import time

from malcolm.core import Attribute, Controller, takes, MethodMeta, REQUIRED
from malcolm.vmetas import PointGeneratorMeta, StringMeta, NumberMeta
from malcolm.statemachines import RunnableDeviceStateMachine


@RunnableDeviceStateMachine.insert
@takes()
class ScanPointTickerController(Controller):

    def create_attributes(self):
        self.value = Attribute(NumberMeta("float64", "Value"))
        yield 'value', self.value, None
        self.generator = Attribute(PointGeneratorMeta("Scan Point Generator"))
        yield "generator", self.generator, None
        self.axis_name = Attribute(StringMeta("Name of the axis"))
        yield "axis_name", self.axis_name, None
        self.exposure = Attribute(NumberMeta("float64", "Exposure time"))
        yield "exposure", self.exposure, None

    @takes("generator", PointGeneratorMeta(
                        description="Generator instance"), REQUIRED,
           "axis_name", StringMeta( description="Specifier for axis"), REQUIRED,
           "exposure", NumberMeta(
                       description="Detector exposure time"), REQUIRED)
    def configure(self, params):
        """
        Configure the controller

        Args:
            generator(PointGenerator): Generator to create points
            axis_name(String): Specifier for axis
            exposure(Double): Exposure time for detector
        """
        self.set_attributes({
            self.generator: params.generator,
            self.axis_name: params.axis_name,
            self.exposure: params.exposure,
        })

    @MethodMeta.wrap_method
    def run(self):
        """
        Start the ticker process

        Yields:
            Point: Scan points from PointGenerator
        """
        axis_name = self.axis_name.value
        for point in self.generator.value.iterator():
            self.value.set_value(point.positions[axis_name])
            time.sleep(self.exposure.value)
