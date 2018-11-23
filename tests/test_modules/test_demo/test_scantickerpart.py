import unittest
from mock import MagicMock, call

from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.modules.demo.parts import ScanTickerPart
from malcolm.core import Context, PartRegistrar


class AlmostFloat(object):
    def __init__(self, val, delta):
        self.val = val
        self.delta = delta

    def __eq__(self, other):
        return abs(self.val - other) <= self.delta


class TestScanTickerPart(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock(spec=Context)
        self.registrar = MagicMock(spec=PartRegistrar)
        self.o = ScanTickerPart(name="AxisTwo", mri="mri")
        self.o.setup(self.registrar)

    def prepare_half_run(self):
        line1 = LineGenerator('AxisOne', 'mm', 0, 2, 3)
        line2 = LineGenerator('AxisTwo', 'mm', 0, 2, 2)
        compound = CompoundGenerator([line1, line2], [], [], 1.0)
        compound.prepare()
        self.o.configure(0, 2, generator=compound, axesToMove=['AxisTwo'])

    def test_configure(self):
        self.prepare_half_run()
        assert self.o._completed_steps == 0
        assert self.o._steps_to_do == 2

    def test_run(self):
        self.prepare_half_run()
        self.registrar.reset_mock()
        self.o.run(self.context)
        assert self.context.mock_calls == [
            call.block_view("mri"),
            call.block_view().counter.put_value(0),
            call.sleep(AlmostFloat(1.0, delta=0.05)),
            call.block_view().counter.put_value(2),
            call.sleep(AlmostFloat(2.0, delta=0.1))]
        assert self.registrar.report.call_count == 2
        assert self.registrar.report.call_args_list[0][0][0].steps == 1
        assert self.registrar.report.call_args_list[1][0][0].steps == 2
