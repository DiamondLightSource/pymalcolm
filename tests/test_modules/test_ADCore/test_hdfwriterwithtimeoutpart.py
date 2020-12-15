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
from malcolm.modules.ADCore.parts import HDFWriterWithTimeoutPart
from malcolm.modules.ADCore.parts.hdfwriterpart import greater_than_zero
from malcolm.modules.ADCore.util import AttributeDatasetType
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.scanning.util import DatasetType
from malcolm.testutil import ChildTestCase

from .test_hdfwriterpart import expected_xml


# Mock child writer
class MockWriterChild:
    def __init__(self) -> None:
        self.uniqueId = Mock()
        self.queueUse = Mock()
        self.uniqueId.value = 0
        self.queueUse.value = 0
        self.done = False

    def run(
        self,
        steps: int,
        interval: float = 0.1,
        queue: int = 0,
        sleep_before_queue: float = 0.5,
    ) -> None:
        self.queueUse.value = queue

        # Simulate incrementing unique IDs
        while self.uniqueId.value < steps:
            self.uniqueId.value += 1
            cothread.Sleep(interval)

        # Run through the queue
        if queue > 0:
            cothread.Sleep(sleep_before_queue)
            while self.queueUse.value > 0:
                self.queueUse.value -= 1
                cothread.Sleep(interval)

    def flushNow(self):
        pass


class TestHdfWriterWithTimeoutPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            hdf_writer_block, self.process, mri="BLOCK:HDF5", prefix="prefix"
        )
        self.process.start()

    def tearDown(self):
        self.process.stop(2)

    def configure_and_check_output(self, on_windows=False):
        energy = LineGenerator("energy", "kEv", 13.0, 15.2, 2)
        spiral = SpiralGenerator(["x", "y"], ["mm", "mm"], [0.0, 0.0], 5.0, scale=2.0)
        generator = CompoundGenerator([energy, spiral], [], [], 0.1)
        generator.prepare()
        fileDir = "/tmp"
        formatName = "xspress3"
        fileTemplate = "thing-%s.h5"
        completed_steps = 0
        steps_to_do = 38
        part_info = {
            "DET": [NDArrayDatasetInfo(2)],
            "PANDA": [
                NDAttributeDatasetInfo.from_attribute_type(
                    "I0", AttributeDatasetType.DETECTOR, "COUNTER1.COUNTER"
                ),
                NDAttributeDatasetInfo.from_attribute_type(
                    "It", AttributeDatasetType.MONITOR, "COUNTER2.COUNTER"
                ),
                NDAttributeDatasetInfo.from_attribute_type(
                    "t1x", AttributeDatasetType.POSITION, "INENC1.VAL"
                ),
            ],
            "STAT": [CalculatedNDAttributeDatasetInfo("sum", "StatsTotal")],
        }
        if on_windows:
            part_info["WINPATH"] = [FilePathTranslatorInfo("Y", "/tmp", "")]
        infos = self.o.on_configure(
            self.context,
            completed_steps,
            steps_to_do,
            part_info,
            generator,
            fileDir,
            formatName,
            fileTemplate,
        )
        assert len(infos) == 8
        assert infos[0].name == "xspress3.data"
        assert infos[0].filename == "thing-xspress3.h5"
        assert infos[0].type == DatasetType.PRIMARY
        assert infos[0].rank == 4
        assert infos[0].path == "/entry/detector/detector"
        assert infos[0].uniqueid == "/entry/NDAttributes/NDArrayUniqueId"

        assert infos[1].name == "xspress3.sum"
        assert infos[1].filename == "thing-xspress3.h5"
        assert infos[1].type == DatasetType.SECONDARY
        assert infos[1].rank == 4
        assert infos[1].path == "/entry/sum/sum"
        assert infos[1].uniqueid == "/entry/NDAttributes/NDArrayUniqueId"

        assert infos[2].name == "I0.data"
        assert infos[2].filename == "thing-xspress3.h5"
        assert infos[2].type == DatasetType.PRIMARY
        assert infos[2].rank == 4
        assert infos[2].path == "/entry/I0.data/I0.data"
        assert infos[2].uniqueid == "/entry/NDAttributes/NDArrayUniqueId"

        assert infos[3].name == "It.data"
        assert infos[3].filename == "thing-xspress3.h5"
        assert infos[3].type == DatasetType.MONITOR
        assert infos[3].rank == 4
        assert infos[3].path == "/entry/It.data/It.data"
        assert infos[3].uniqueid == "/entry/NDAttributes/NDArrayUniqueId"

        assert infos[4].name == "t1x.value"
        assert infos[4].filename == "thing-xspress3.h5"
        assert infos[4].type == DatasetType.POSITION_VALUE
        assert infos[4].rank == 4
        assert infos[4].path == "/entry/t1x.value/t1x.value"
        assert infos[4].uniqueid == "/entry/NDAttributes/NDArrayUniqueId"

        assert infos[5].name == "energy.value_set"
        assert infos[5].filename == "thing-xspress3.h5"
        assert infos[5].type == DatasetType.POSITION_SET
        assert infos[5].rank == 1
        assert infos[5].path == "/entry/detector/energy_set"
        assert infos[5].uniqueid == ""

        assert infos[6].name == "x.value_set"
        assert infos[6].filename == "thing-xspress3.h5"
        assert infos[6].type == DatasetType.POSITION_SET
        assert infos[6].rank == 1
        assert infos[6].path == "/entry/detector/x_set"
        assert infos[6].uniqueid == ""

        assert infos[7].name == "y.value_set"
        assert infos[7].filename == "thing-xspress3.h5"
        assert infos[7].type == DatasetType.POSITION_SET
        assert infos[7].rank == 1
        assert infos[7].path == "/entry/detector/y_set"
        assert infos[7].uniqueid == ""

        expected_xml_filename_local = "/tmp/BLOCK_HDF5-layout.xml"
        if on_windows:
            expected_xml_filename_remote = "Y:\\BLOCK_HDF5-layout.xml"
            expected_filepath = "Y:" + os.sep
        else:
            expected_xml_filename_remote = expected_xml_filename_local
            expected_filepath = "/tmp" + os.sep
        # Wait for the start_future so the post gets through to our child
        # even on non-cothread systems
        self.o.start_future.result(timeout=1)
        # Same set of calls as HDFWriterPart, but also set position Mode to false after
        assert self.child.handled_requests.mock_calls == [
            call.put("positionMode", True),
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
            call.put("extraDimSize3", 1),
            call.put("extraDimSize4", 1),
            call.put("extraDimSize5", 1),
            call.put("extraDimSize6", 1),
            call.put("extraDimSize7", 1),
            call.put("extraDimSize8", 1),
            call.put("extraDimSize9", 1),
            call.put("extraDimSizeN", 20),
            call.put("extraDimSizeX", 2),
            call.put("extraDimSizeY", 1),
            call.put("numExtraDims", 1),
            call.put("posNameDim3", ""),
            call.put("posNameDim4", ""),
            call.put("posNameDim5", ""),
            call.put("posNameDim6", ""),
            call.put("posNameDim7", ""),
            call.put("posNameDim8", ""),
            call.put("posNameDim9", ""),
            call.put("posNameDimN", "d1"),
            call.put("posNameDimX", "d0"),
            call.put("posNameDimY", ""),
            call.put("flushAttrPerNFrames", 0),
            call.put("flushDataPerNFrames", 38),
            call.put("xmlLayout", expected_xml_filename_remote),
            call.put("numCapture", 0),
            call.post("start"),
            call.when_value_matches("arrayCounterReadback", greater_than_zero, None),
            call.put("positionMode", False),
        ]
        with open(expected_xml_filename_local) as f:
            actual_xml = f.read().replace(">", ">\n")
        # Check the layout filename Malcolm uses for file creation
        assert self.o.layout_filename == expected_xml_filename_local
        return actual_xml

    @staticmethod
    def mock_xml_is_valid_check(part):
        mock_xml_layout_value = MagicMock(name="mock_xml_layout_value")
        mock_xml_layout_value.return_value = True
        part._check_xml_is_valid = mock_xml_layout_value

    def test_init(self):
        self.o = HDFWriterWithTimeoutPart(name="m", mri="BLOCK:HDF5", timeout=1.0)
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        c = RunnableController("mri", "/tmp")
        c.add_part(self.o)
        self.process.add_controller(c)
        b = c.block_view()
        assert list(b.configure.meta.takes.elements) == [
            "generator",
            "fileDir",
            "axesToMove",
            "formatName",
            "fileTemplate",
        ]

    def test_configure(self):
        self.mock_when_value_matches(self.child)
        self.o = HDFWriterWithTimeoutPart(name="m", mri="BLOCK:HDF5", timeout=1.0)
        self.mock_xml_is_valid_check(self.o)
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        actual_xml = self.configure_and_check_output()

        actual_tree = ElementTree.XML(actual_xml)
        expected_tree = ElementTree.XML(expected_xml)
        assert ElementTree.dump(actual_tree) == ElementTree.dump(expected_tree)

    def test_honours_write_all_attributes_flag(self):
        self.mock_when_value_matches(self.child)
        self.o = HDFWriterWithTimeoutPart(
            name="m", mri="BLOCK:HDF5", timeout=1.0, write_all_nd_attributes=False
        )
        self.mock_xml_is_valid_check(self.o)
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        actual_xml = self.configure_and_check_output()

        actual_tree = ElementTree.XML(actual_xml)
        expected_tree = ElementTree.XML(expected_xml)
        assert ElementTree.dump(actual_tree) == ElementTree.dump(expected_tree)

    def test_configure_windows(self):
        self.mock_when_value_matches(self.child)
        self.o = HDFWriterWithTimeoutPart(
            name="m", mri="BLOCK:HDF5", timeout=1.0, runs_on_windows=True
        )
        self.mock_xml_is_valid_check(self.o)
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        actual_xml = self.configure_and_check_output(on_windows=True)

        actual_tree = ElementTree.XML(actual_xml)
        expected_tree = ElementTree.XML(expected_xml)
        assert ElementTree.dump(actual_tree) == ElementTree.dump(expected_tree)

    def test_on_run(self):

        # Create the writer part
        self.o = HDFWriterWithTimeoutPart(
            name="m", mri="BLOCK:HDF5", timeout=0.2, runs_on_windows=True
        )

        # Create and set up mocks
        context_mock = Mock(name="context_mock")
        child_mock = MockWriterChild()
        context_mock.block_view.return_value = child_mock
        steps = 10

        # Start running the child mock
        cothread.Spawn(child_mock.run, steps)

        # Now run our part
        self.o.on_run(context_mock)

        # Make sure the thread finishes
        assert child_mock.uniqueId.value == steps

    def test_on_run_with_queue(self):

        # Create the writer part
        self.o = HDFWriterWithTimeoutPart(
            name="m", mri="BLOCK:HDF5", timeout=0.1, runs_on_windows=True
        )

        # Create and set up mocks
        context_mock = Mock(name="context_mock")
        child_mock = MockWriterChild()
        context_mock.block_view.return_value = child_mock
        steps = 10
        queue = 10

        # Start running the child mock
        cothread.Spawn(child_mock.run, steps, queue=queue)

        # Now run our part
        self.o.on_run(context_mock)

        # Make sure the thread finishes
        assert child_mock.uniqueId.value == steps
        assert child_mock.queueUse.value == 0
