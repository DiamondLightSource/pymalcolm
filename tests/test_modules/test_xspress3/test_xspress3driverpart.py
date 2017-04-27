import unittest
from mock import MagicMock, ANY, call

from scanpointgenerator import LineGenerator, CompoundGenerator
from malcolm.core import call_with_params, Context
from malcolm.modules.xspress3.parts import Xspress3DriverPart


class TestXspress3DetectorDriverPart(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock(spec=Context)
        self.o = call_with_params(
            Xspress3DriverPart, readoutTime=0.002, name="m", mri="mri")
        list(self.o.create_attributes())

    def test_configure(self):
        params = MagicMock()
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3000, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2000)
        params.generator = CompoundGenerator([ys, xs], [], [], 0.1)
        params.generator.prepare()
        completed_steps = 0
        steps_to_do = 2000*3000
        part_info = ANY
        self.o.configure(
            self.context, completed_steps, steps_to_do, part_info, params)
        assert self.context.mock_calls == [
            call.unsubscribe_all(),
            call.block_view("mri"),
            call.block_view().put_attribute_values_async(dict(
                pointsPerRow=15000,
                triggerMode='Hardware')),
            call.block_view().put_attribute_values_async(dict(
                numImages=6000000,
                arrayCallbacks=True,
                arrayCounter=0,
                imageMode='Multiple')),
            call.block_view().exposure.put_value_async(0.098),
            call.block_view().put_attribute_values_async().append(ANY),
            call.block_view().put_attribute_values_async().__iadd__(ANY),
            call.wait_all_futures(ANY),
            call.block_view().start_async()]
