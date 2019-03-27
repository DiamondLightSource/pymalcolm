import os
import shutil
import tempfile
import time
import unittest

import h5py
from cothread import cothread
from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.modules.demo.blocks import detector_block
from malcolm.core import Process
from malcolm.modules.scanning.util import DatasetType


class TestDetectorBlock(unittest.TestCase):
    def setUp(self):
        self.p = Process("proc")
        for c in detector_block("mri", config_dir="/tmp"):
            self.p.add_controller(c)
        self.p.start()
        self.b = self.p.block_view("mri")
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        self.p.stop(timeout=2)
        shutil.rmtree(self.tmpdir)

    def test_init(self):
        assert list(self.b) == [
            'meta', 'health', 'state', 'disable', 'reset', 'mri', 'layout',
            'design', 'exports', 'modified', 'save', 'completedSteps',
            'configuredSteps', 'totalSteps', 'validate', 'configure', 'run',
            'abort', 'pause', 'resume', 'datasets']
        assert list(self.b.configure.meta.takes.elements) == [
            'generator', 'fileDir', 'axesToMove', 'formatName', 'fileTemplate'
        ]

    def make_generator(self):
        linex = LineGenerator('stage_x', 'mm', 0, 2, 3, alternate=True)
        liney = LineGenerator('stage_y', 'mm', 0, 2, 2)
        compound = CompoundGenerator([liney, linex], [], [], 0.5)
        return compound

    def test_scan(self):
        self.b.configure(self.make_generator(), self.tmpdir)
        assert list(self.b.datasets.value.rows()) == [
            ['det.data', 'det.h5', DatasetType.PRIMARY, 4, '/entry/data',
             '/entry/uid'],
            ['det.sum', 'det.h5', DatasetType.SECONDARY, 4, '/entry/sum',
             '/entry/uid']
        ]
        filepath = os.path.join(self.tmpdir, "det.h5")
        with h5py.File(filepath, "r") as hdf:
            assert hdf["/entry/data"].shape == (1, 1, 240, 320)
            assert hdf["/entry/sum"].shape == (1, 1, 1, 1)
            assert hdf["/entry/uid"].shape == (1, 1, 1, 1)
            assert hdf["/entry/uid"][0][0][0][0] == 0
            fs = self.b.run_async()
            # Wait for 2 frames to be written (but not reported yet)
            cothread.Sleep(0.8)
            assert self.b.completedSteps.value == 1
            assert hdf["/entry/data"].shape == (1, 2, 240, 320)
            assert hdf["/entry/sum"].shape == (1, 2, 1, 1)
            assert hdf["/entry/uid"].shape == (1, 2, 1, 1)
            assert hdf["/entry/sum"][0][0][0][0] == 837336.0
            assert hdf["/entry/uid"][0][0][0][0] == 1
            assert hdf["/entry/sum"][0][1][0][0] == 3904536.0
            assert hdf["/entry/uid"][0][1][0][0] == 2
            # pause
            self.b.pause(lastGoodStep=3)
            assert self.b.completedSteps.value == 3
            # resume
            self.b.resume()
            # Wait for the rest
            before_end = time.time()
            fs.result(timeout=10)
            self.assertAlmostEqual(time.time() - before_end, 1.5, delta=0.25)
            # Check the rest of the data, including the blank
            assert hdf["/entry/data"].shape == (2, 3, 240, 320)
            assert hdf["/entry/sum"].shape == (2, 3, 1, 1)
            assert hdf["/entry/uid"].shape == (2, 3, 1, 1)
            assert hdf["/entry/sum"][0][2][0][0] == 0
            assert hdf["/entry/uid"][0][2][0][0] == 0
            assert hdf["/entry/sum"][1][2][0][0] == 7195916.0
            assert hdf["/entry/uid"][1][2][0][0] == 7
            assert hdf["/entry/sum"][1][0][0][0] == 837336.0
            assert hdf["/entry/uid"][1][0][0][0] == 9
            # Reset to close the file
            self.b.reset()
