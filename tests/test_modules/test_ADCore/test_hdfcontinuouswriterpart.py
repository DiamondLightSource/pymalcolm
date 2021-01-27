import os
from xml.etree import ElementTree

import cothread
from mock import MagicMock, Mock, call
from scanpointgenerator import CompoundGenerator, LineGenerator, SpiralGenerator

from malcolm.core import Context, Process
from malcolm.modules.ADCore.blocks import hdf_writer_block
from malcolm.modules.ADCore.infos import (
    CalculatedNDAttributeDatasetInfo,
    FilePathTranslatorInfo,
    NDArrayDatasetInfo,
    NDAttributeDatasetInfo,
)
from malcolm.modules.ADCore.parts import HDFContinuousWriterPart
from malcolm.modules.ADCore.parts.hdfwriterpart import greater_than_zero
from malcolm.modules.ADCore.util import AttributeDatasetType
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.scanning.util import DatasetType
from malcolm.testutil import ChildTestCase

from .test_hdfwriterpart import expected_xml


class TestHDFContinuousWriterPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            hdf_writer_block, self.process, mri="BLOCK:HDF5", prefix="prefix"
        )
        self.process.start()

    def tearDown(self):
        self.process.stop(2)

    def configure(self, on_windows=False):
        energy = LineGenerator("energy", "kEv", 13.0, 15.2, 2)
        spiral = SpiralGenerator(["x", "y"], ["mm", "mm"], [0.0, 0.0], 5.0, scale=2.0)
        generator = CompoundGenerator([energy, spiral], [], [], 0.1)
        generator.prepare()
        fileDir = "/tmp"
        formatName = "xspress3"
        fileTemplate = "thing-%s.h5"
        part_info = {"DET": [NDArrayDatasetInfo(2)]}
        if on_windows:
            part_info["WINPATH"] = [FilePathTranslatorInfo("Y", "/tmp", "")]
        infos = self.o.on_configure(
            self.context, part_info, generator, fileDir, formatName, fileTemplate,
        )
        assert len(infos) == 4
        assert infos[0].name == "xspress3.data"
        assert infos[0].filename == "thing-xspress3.h5"
        assert infos[0].type == DatasetType.PRIMARY
        assert infos[0].rank == 4
        assert infos[0].path == "/entry/detector/detector"
        assert infos[0].uniqueid == "/entry/NDAttributes/NDArrayUniqueId"

        assert infos[1].name == "energy.value_set"
        assert infos[1].filename == "thing-xspress3.h5"
        assert infos[1].type == DatasetType.POSITION_SET
        assert infos[1].rank == 1
        assert infos[1].path == "/entry/detector/energy_set"
        assert infos[1].uniqueid == ""

        assert infos[2].name == "x.value_set"
        assert infos[2].filename == "thing-xspress3.h5"
        assert infos[2].type == DatasetType.POSITION_SET
        assert infos[2].rank == 1
        assert infos[2].path == "/entry/detector/x_set"
        assert infos[2].uniqueid == ""

        assert infos[3].name == "y.value_set"
        assert infos[3].filename == "thing-xspress3.h5"
        assert infos[3].type == DatasetType.POSITION_SET
        assert infos[3].rank == 1
        assert infos[3].path == "/entry/detector/y_set"
        assert infos[3].uniqueid == ""

        if on_windows:
            expected_filepath = "Y:" + os.sep
        else:
            expected_filepath = "/tmp" + os.sep
        # Same set of calls as HDFWriterPart, but also set position Mode to false after
        assert self.child.handled_requests.mock_calls == [
            call.put("positionMode", False),
            call.put("arrayCounter", 0),
            call.put("dimAttDatasets", True),
            call.put("enableCallbacks", True),
            call.put("fileName", "xspress3"),
            call.put("filePath", expected_filepath),
            call.put("fileTemplate", "%sthing-%s.h5"),
            call.put("fileWriteMode", "Stream"),
            call.put("lazyOpen", True),
            call.put("storeAttr", True),
            call.put("swmrMode", True),
            call.put("flushAttrPerNFrames", 0),
            call.put("flushDataPerNFrames", 1),
            call.put("numCapture", 0),
            call.post("start"),
            call.when_value_matches("arrayCounterReadback", greater_than_zero, None),
        ]

    def test_init(self):
        self.o = HDFContinuousWriterPart(name="m", mri="BLOCK:HDF5")
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        c = RunnableController("mri", "/tmp")
        c.add_part(self.o)
        self.process.add_controller(c)
        b = c.block_view()
        assert list(b.configure.meta.takes.elements) == [
            "generator",
            "fileDir",
            "axesToMove",
            "breakpoints",
            "formatName",
            "fileTemplate",
        ]

    def test_configure(self):
        self.mock_when_value_matches(self.child)
        self.o = HDFContinuousWriterPart(name="m", mri="BLOCK:HDF5")
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.configure()

    def test_honours_write_all_attributes_flag(self):
        self.mock_when_value_matches(self.child)
        self.o = HDFContinuousWriterPart(
            name="m", mri="BLOCK:HDF5", write_all_nd_attributes=False
        )
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.configure()

    def test_configure_windows(self):
        self.mock_when_value_matches(self.child)
        self.o = HDFContinuousWriterPart(
            name="m", mri="BLOCK:HDF5", runs_on_windows=True
        )
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.configure(on_windows=True)

    def test_on_run(self):
        self.o = HDFContinuousWriterPart(
            name="m", mri="BLOCK:HDF5", runs_on_windows=True
        )
        context_mock = Mock(name="context_mock")

        self.o.on_run(context_mock)

        context_mock.wait_all_futures.assert_called_once_with(self.o.array_future)
