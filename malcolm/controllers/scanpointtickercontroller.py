import numpy
import time

from malcolm.core.attribute import Attribute
from malcolm.core.controller import Controller
from malcolm.core.mapmeta import REQUIRED
from malcolm.core.method import takes, Method
from malcolm.core.pointgeneratormeta import PointGeneratorMeta
from malcolm.core.stringmeta import StringMeta
from malcolm.core.numbermeta import NumberMeta
from malcolm.core.runnabledevicestatemachine import RunnableDeviceStateMachine


@RunnableDeviceStateMachine.insert
class ScanPointTickerController(Controller):

    def __init__(self, block):
        super(ScanPointTickerController, self).__init__(block)

    def create_attributes(self):
        self.value = Attribute("value",
                NumberMeta("meta", "Value", numpy.float64))
        yield self.value
        self.generator = Attribute(
            "generator", PointGeneratorMeta("meta", "Scan Point Generator"))
        yield self.generator
        self.axis_name = Attribute(
            "axis_name", StringMeta("meta", "Name of the axis"))
        yield self.axis_name
        self.exposure = Attribute(
            "exposure", NumberMeta("meta", "Exposure time", numpy.float64))
        yield self.exposure

    @takes(PointGeneratorMeta("generator", "Generator instance"), REQUIRED,
           StringMeta("axis_name", "Specifier for axis"), REQUIRED,
           NumberMeta("exposure", "Detector exposure time", numpy.float64), REQUIRED)
    def configure(self, generator, axis_name, exposure):
        """
        Configure the controller

        Args:
            generator(PointGenerator): Generator to create points
            axis_name(String): Specifier for axis
            exposure(Double): Exposure time for detector
        """

        self.generator.set_value(generator)
        self.axis_name.set_value(axis_name)
        self.exposure.set_value(exposure)
        self.block.notify_subscribers()

    @Method.wrap_method
    def run(self):
        """
        Start the ticker process

        Yields:
            Point: Scan points from PointGenerator
        """

        for point in self.generator.value.iterator():
            self.value.set_value(point)
            self.block.notify_subscribers()
            time.sleep(self.exposure.value)
