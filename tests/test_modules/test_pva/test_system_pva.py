import unittest

from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.core import Process, json_encode
from malcolm.modules.builtin.blocks import proxy_block
from malcolm.modules.builtin.util import ExportTable
from malcolm.modules.demo.blocks import ticker_block
from malcolm.modules.pva.blocks import pva_client_block, pva_server_block


class TestSystemPVA(unittest.TestCase):

    def setUp(self):
        self.process = Process("proc")
        for controller in \
                ticker_block(mri="TESTTICKER", config_dir="/tmp") + \
                pva_server_block(mri="PVA-SERVER"):
            self.process.add_controller(controller)
        self.process.start()
        self.process2 = Process("proc2")
        for controller in \
                pva_client_block(mri="PVA-CLIENT") + \
                proxy_block(mri="TESTTICKER", comms="PVA-CLIENT"):
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
        src_block = self.process.block_view("TESTTICKER")
        block = self.process2.block_view("TESTTICKER")
        for k in src_block:
            assert json_encode(block[k].to_dict(), indent=2) == \
                   json_encode(src_block[k].to_dict(), indent=2)

    def test_init(self):
        self.check_blocks_equal()

    def test_validate(self):
        block = self.process2.block_view("TESTTICKER")
        self.check_blocks_equal()
        generator = self.make_generator()
        params = block.validate(generator, axesToMove=["x", "y"])
        assert params == dict(
            axesToMove=["x", "y"],
            exceptionStep=0,
            generator=generator.to_dict(),
        )
        # Sent 2 things (exceptionStep is zero by default)
        assert block.validate.took.value == params
        assert block.validate.took.present == ["generator", "axesToMove"]
        # Got back 3 things
        assert block.validate.returned.value == params
        assert block.validate.returned.present == [
            "generator", "axesToMove", "exceptionStep"]
        self.check_blocks_equal()

    def test_configure(self):
        block = self.process2.block_view("TESTTICKER")
        self.check_blocks_equal()
        generator = self.make_generator()
        block.configure(generator, axesToMove=["x", "y"])
        # TODO: ordering is not maintained in PVA, so may need to wait before
        #       get
        # block._context.sleep(0.1)
        assert "Armed" == block.state.value
        assert block.configure.took.value == dict(
            generator=generator.to_dict(), axesToMove=["x", "y"],
            exceptionStep=0)
        assert block.configure.took.present == ["generator", "axesToMove"]
        assert block.configure.returned.value == {}
        assert block.configure.returned.present == []
        self.check_blocks_equal()

    def test_exports(self):
        block = self.process2.block_view("TESTTICKER")
        fields = [
            'meta',
            'health',
            'state',
            'disable',
            'reset',
            'mri',
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
        ##################### block.reset()
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

