import shutil
import tempfile
import unittest

from scanpointgenerator import CompoundGenerator, LineGenerator

from malcolm.core import Process
from malcolm.modules.demo.blocks import detector_block, motion_block, scan_1det_block
from malcolm.modules.scanning.util import DatasetType, DetectorTable
from malcolm.testutil import PublishController


class TestScanBlock(unittest.TestCase):
    def setUp(self):
        self.p = Process("proc")
        for c in (
            detector_block("DETECTOR", config_dir="/tmp")
            + motion_block("MOTION", config_dir="/tmp")
            + scan_1det_block("SCANMRI", config_dir="/tmp")
        ):
            self.p.add_controller(c)
        self.pub = PublishController("PUB")
        self.p.add_controller(self.pub)
        self.p.start()
        self.b = self.p.block_view("SCANMRI")
        self.bd = self.p.block_view("DETECTOR")
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        self.p.stop(timeout=2)
        shutil.rmtree(self.tmpdir)

    def test_init(self):
        assert self.b.label.value == "Mapping x, y with demo detector"
        assert list(self.b.configure.meta.defaults["detectors"].rows()) == [
            [True, "DET", "DETECTOR", 0.0, 1]
        ]
        assert self.pub.published == [
            "SCANMRI",
            "PUB",
            "DETECTOR",
            "MOTION",
            "MOTION:COUNTERX",
            "MOTION:COUNTERY",
        ]

    def make_generator(self):
        linex = LineGenerator("x", "mm", 0, 2, 3, alternate=True)
        liney = LineGenerator("y", "mm", 0, 2, 2)
        compound = CompoundGenerator([liney, linex], [], [], 0.1)
        return compound

    def test_validate(self):
        compound = self.make_generator()
        detectors = DetectorTable.from_rows([[True, "DET", "DETECTOR", 0.0, 1]])
        ret = self.b.validate(compound, self.tmpdir, detectors=detectors)
        assert list(ret["detectors"].rows()) == [[True, "DET", "DETECTOR", 0.098995, 1]]

    def prepare_half_run(self):
        compound = self.make_generator()
        self.b.configure(
            compound, self.tmpdir, axesToMove=["x"], fileTemplate="my-%s.h5"
        )

    def test_configure(self):
        self.prepare_half_run()
        assert list(self.b.datasets.value.rows()) == [
            [
                "DET.data",
                "my-DET.h5",
                DatasetType.PRIMARY,
                4,
                "/entry/data",
                "/entry/uid",
            ],
            [
                "DET.sum",
                "my-DET.h5",
                DatasetType.SECONDARY,
                4,
                "/entry/sum",
                "/entry/uid",
            ],
            [
                "y.value_set",
                "my-DET.h5",
                DatasetType.POSITION_SET,
                1,
                "/entry/y_set",
                "",
            ],
            [
                "x.value_set",
                "my-DET.h5",
                DatasetType.POSITION_SET,
                1,
                "/entry/x_set",
                "",
            ],
        ]
        for b in (self.b, self.bd):
            assert b.completedSteps.value == 0
            assert b.configuredSteps.value == 3
            assert b.totalSteps.value == 6

    def test_run(self):
        self.prepare_half_run()
        assert self.b.state.value == "Armed"
        self.b.run()
        for b in (self.b, self.bd):
            assert b.completedSteps.value == 3
            assert b.configuredSteps.value == 6
            assert b.totalSteps.value == 6
            assert b.state.value == "Armed"
        self.b.run()
        for b in (self.b, self.bd):
            assert b.completedSteps.value == 6
            assert b.configuredSteps.value == 6
            assert b.totalSteps.value == 6
            assert b.state.value == "Finished"
        self.b.reset()
        for b in (self.b, self.bd):
            assert b.state.value == "Ready"
