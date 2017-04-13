import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, MagicMock, ANY, call

from scanpointgenerator import LineGenerator, CompoundGenerator
from malcolm.core import call_with_params, Context
from malcolm.parts.xspress3.xspress3driverpart import Xspress3DriverPart


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
            call.block_view("mri"),
            call.block_view().pointsPerRow.put_value(15000),
            # TODO: this call is temporary until it is a config value
            call.block_view().triggerMode.put_value('Hardware'),
            call.unsubscribe_all(),
            call.block_view('mri'),
            call.block_view().put_attribute_values(dict(
                numImages=6000000,
                arrayCallbacks=True,
                arrayCounter=0,
                exposure=0.098000000000000004,
                imageMode='Multiple')),
            call.block_view().start_async()]

if __name__ == "__main__":
    unittest.main(verbosity=2)
