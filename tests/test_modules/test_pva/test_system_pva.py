import shutil
import tempfile
import unittest

import pytest
from annotypes import json_encode
from scanpointgenerator import CompoundGenerator, LineGenerator

from malcolm.core import Process
from malcolm.modules.builtin.blocks import proxy_block
from malcolm.modules.builtin.util import ExportTable
from malcolm.modules.demo.blocks import detector_block, motion_block
from malcolm.modules.pva.blocks import pva_client_block, pva_server_block


class TestSystemDetectorPVA(unittest.TestCase):
    def setUp(self):
        self.process = Process("proc")
        for controller in detector_block(
            mri="TESTDET", config_dir="/tmp"
        ) + pva_server_block(mri="PVA-SERVER"):
            self.process.add_controller(controller)
        self.process.start()
        self.process2 = Process("proc2")
        for controller in pva_client_block(mri="PVA-CLIENT") + proxy_block(
            mri="TESTDET", comms="PVA-CLIENT"
        ):
            self.process2.add_controller(controller)
        self.process2.start()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        self.process.stop(timeout=2)
        self.process2.stop(timeout=2)
        shutil.rmtree(self.tmpdir)

    def make_generator(self):
        line1 = LineGenerator("y", "mm", 0, 3, 3)
        line2 = LineGenerator("x", "mm", 1, 2, 2)
        compound = CompoundGenerator([line1, line2], [], [], duration=0.05)
        return compound

    def check_blocks_equal(self):
        src_block = self.process.block_view("TESTDET")
        block = self.process2.block_view("TESTDET")
        for k in src_block:
            assert json_encode(block[k].to_dict(), indent=2) == json_encode(
                src_block[k].to_dict(), indent=2
            )

    def test_init(self):
        self.check_blocks_equal()

    def test_validate(self):
        src_block = self.process.block_view("TESTDET")
        block = self.process2.block_view("TESTDET")
        self.check_blocks_equal()
        generator = self.make_generator()
        an_empty_list = pytest.approx([])  # see comment in test_configure()
        validated = dict(
            generator=generator.to_dict(),
            fileDir=self.tmpdir,
            axesToMove=["y", "x"],
            breakpoints=an_empty_list,
            fileTemplate="%s.h5",
            formatName="det",
            exposure=0.0489975,
        )
        assert validated == block.validate(generator, self.tmpdir)
        # Sent 2 things, other zeroed
        assert block.validate.took.value == dict(
            generator=generator.to_dict(),
            fileDir=self.tmpdir,
            axesToMove=[],
            breakpoints=an_empty_list,
            fileTemplate="",
            formatName="",
            exposure=0,
        )
        assert block.validate.took.present == ["generator", "fileDir"]
        # Got back defaulted things
        assert block.validate.returned.value == validated
        all_args = [
            "generator",
            "fileDir",
            "axesToMove",
            "breakpoints",
            "exposure",
            "formatName",
            "fileTemplate",
        ]
        assert list(block.validate.meta.takes.elements) == all_args
        assert src_block.validate.returned.present == all_args
        assert block.validate.returned.present == all_args
        self.check_blocks_equal()

    def test_configure(self):
        block = self.process2.block_view("TESTDET")
        self.check_blocks_equal()
        generator = self.make_generator()
        # an_empty_list = np.ndarray(shape=(0,), dtype=np.int64)
        # for some reason, the above is not equating to array([]) in Py3
        an_empty_list = pytest.approx([])
        validated = dict(
            generator=generator.to_dict(),
            fileDir=self.tmpdir,
            axesToMove=["x", "y"],
            fileTemplate="%s.h5",
            breakpoints=an_empty_list,
            formatName="det",
            exposure=0.0489975,
        )
        params = block.configure(generator, self.tmpdir, axesToMove=["x", "y"])

        assert validated == params
        # TODO: ordering is not maintained in PVA, so may need to wait before
        #       get
        # block._context.sleep(0.1)
        assert "Armed" == block.state.value
        assert block.configure.took.value == dict(
            generator=generator.to_dict(),
            axesToMove=["x", "y"],
            breakpoints=an_empty_list,
            exposure=0.0,
            fileDir=self.tmpdir,
            fileTemplate="",
            formatName="",
        )
        assert block.configure.took.present == ["generator", "fileDir", "axesToMove"]
        assert block.configure.returned.value == validated
        assert block.configure.returned.present == [
            "generator",
            "fileDir",
            "axesToMove",
            "breakpoints",
            "exposure",
            "formatName",
            "fileTemplate",
        ]
        self.check_blocks_equal()
        # Check the NTTable
        from p4p.client.cothread import Context

        with Context("pva") as ctxt:
            table = ctxt.get("TESTDET.datasets")
            assert table.getID() == "epics:nt/NTTable:1.0"
            assert dict(table.value.items()) == dict(
                filename=["det.h5", "det.h5", "det.h5", "det.h5"],
                name=["det.data", "det.sum", "y.value_set", "x.value_set"],
                path=["/entry/data", "/entry/sum", "/entry/y_set", "/entry/x_set"],
                rank=pytest.approx([4, 4, 1, 1]),
                type=["primary", "secondary", "position_set", "position_set"],
                uniqueid=["/entry/uid", "/entry/uid", "", ""],
            )
            labels = ["name", "filename", "type", "rank", "path", "uniqueid"]
            assert list(table.meta.elements) == labels
            assert table.labels == labels


class TestSystemMotionPVA(unittest.TestCase):
    def setUp(self):
        self.process = Process("proc")
        for controller in motion_block(
            mri="TESTMOTION", config_dir="/tmp"
        ) + pva_server_block(mri="PVA-SERVER"):
            self.process.add_controller(controller)
        self.process.start()
        self.process2 = Process("proc2")
        for controller in pva_client_block(mri="PVA-CLIENT") + proxy_block(
            mri="TESTMOTION", comms="PVA-CLIENT"
        ):
            self.process2.add_controller(controller)
        self.process2.start()

    def test_exports(self):
        block = self.process2.block_view("TESTMOTION")
        fields = [
            "meta",
            "health",
            "state",
            "disable",
            "reset",
            "mri",
            "layout",
            "design",
            "exports",
            "modified",
            "save",
            "xMove",
            "yMove",
        ]
        assert list(block) == fields
        block.xMove(2)
        block.yMove(3)
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
