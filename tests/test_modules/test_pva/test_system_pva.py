import unittest

from p4p.client.raw import RemoteError
from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.core import Process
from malcolm.modules.builtin.blocks import proxy_block
from malcolm.modules.builtin.util import ExportTable
from malcolm.modules.demo.blocks import ticker_block
from malcolm.modules.pva.blocks import pva_client_block, pva_server_block


class TestSystemPVA(unittest.TestCase):

    def setUp(self):
        self.process = Process("proc")
        for controller in \
                ticker_block(mri="TICKER", config_dir="/tmp") + \
                pva_server_block(mri="PVA-SERVER"):
            self.process.add_controller(controller)
        self.process.start()
        self.process2 = Process("proc2")
        for controller in \
                pva_client_block(mri="PVA-CLIENT") + \
                proxy_block(mri="TICKER", comms="PVA-CLIENT",
                            use_cothread=True):
            self.process2.add_controller(controller)
        self.process2.start()

    def tearDown(self):
        self.process.stop(timeout=2)
        self.process2.stop(timeout=2)

    def make_generator(self):
        line1 = LineGenerator('y', 'mm', 0, 3, 3)
        line2 = LineGenerator('x', 'mm', 1, 2, 2)
        compound = CompoundGenerator([line1, line2], [], [], duration=0.05)
        return compound

    def check_blocks_equal(self):
        src_block = self.process.block_view("TICKER")
        block = self.process2.block_view("TICKER")
        for k in src_block:
            assert block[k].to_dict() == src_block[k].to_dict()

    def test_init(self):
        self.check_blocks_equal()

    def test_validate(self):
        block = self.process2.block_view("TICKER")
        generator = self.make_generator()
        params = block.validate(generator, axesToMove=["x", "y"])
        assert params == dict(
            axesToMove=["x", "y"],
            exceptionStep=0,
            generator=generator.to_dict(),
        )

    def test_configure(self):
        block = self.process2.block_view("TICKER")
        generator = self.make_generator()
        block.configure(generator, axesToMove=["x", "y"])
        # TODO: ordering is not maintained in PVA, so need to wait before get
        block._context.sleep(0.1)
        assert "Armed" == block.state.value
        self.check_blocks_equal()

    def test_exports(self):
        block = self.process2.block_view("TICKER")
        fields = [
            'meta',
            'health',
            'state',
            'disable',
            'reset',
            'layout',
            'design',
            'exports',
            'modified',
            'save',
            'completedSteps',
            'configuredSteps',
            'totalSteps',
            'validate',
            'configure',
            'run',
            'abort',
            'pause',
            'resume']
        assert list(block) == fields
        generator = self.make_generator()
        block.configure(generator, axesToMove=["x", "y"])
        block.run()
        # Export X
        t = ExportTable(source=["x.counter"], export=["xValue"])
        block.exports.put_value(t)
        assert list(block) == fields + ["xValue"]
        assert block.xValue.value == 2.0
        # Export Y
        t = ExportTable(source=["y.counter"], export=["yValue"])
        block.exports.put_value(t)
        assert list(block) == fields + ["yValue"]
        assert block.yValue.value == 3.0
        # Export Nothing
        t = ExportTable(source=[], export=[])
        block.exports.put_value(t)
        assert list(block) == fields

