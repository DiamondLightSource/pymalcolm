import numpy
import time

from malcolm.core.attribute import Attribute
from malcolm.core.controller import Controller
from malcolm.core.method import takes, Method, REQUIRED
from malcolm.metas import PointGeneratorMeta, StringMeta, NumberMeta
from malcolm.statemachines import RunnableDeviceStateMachine


@RunnableDeviceStateMachine.insert
@takes()
class ScanPointTickerController(Controller):

    def create_attributes(self):
        self.value = Attribute(NumberMeta(description="Value"))
        self.value.meta.set_dtype('float64')
        yield 'value', self.value
        self.generator = Attribute(
            PointGeneratorMeta(description="Scan Point Generator"))
        yield "generator", self.generator
        self.axis_name = Attribute(StringMeta(description="Name of the axis"))
        yield "axis_name", self.axis_name
        self.exposure = Attribute(NumberMeta(description="Exposure time"))
        self.value.meta.set_dtype('float64')
        yield "exposure", self.exposure

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

        self.generator.set_value(params.generator)
        self.axis_name.set_value(params.axis_name)
        self.exposure.set_value(params.exposure)
        self.exposure.meta.set_dtype('float64')
        self.block.notify_subscribers()

    @Method.wrap_method
    def run(self):
        """
        Start the ticker process

        Yields:
            Point: Scan points from PointGenerator
        """
        axis_name = self.axis_name.value
        for point in self.generator.value.iterator():
            self.value.set_value(point.positions[axis_name])
            self.block.notify_subscribers()
            time.sleep(self.exposure.value)
