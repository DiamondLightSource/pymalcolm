import os
from mock import MagicMock, call, ANY

from scanpointgenerator import LineGenerator, CompoundGenerator, SpiralGenerator

from malcolm.core import Context, call_with_params, Process, Future
from malcolm.modules.ADCore.blocks import hdf_writer_block
from malcolm.modules.ADCore.parts import HDFWriterPart
from malcolm.modules.ADCore.infos import NDArrayDatasetInfo, \
    CalculatedNDAttributeDatasetInfo, NDAttributeDatasetInfo, UniqueIdInfo
from malcolm.testutil import ChildTestCase


class TestHDFWriterPart(ChildTestCase):
    maxDiff = None

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            hdf_writer_block, self.process,
            mri="BLOCK-HDF5", prefix="prefix")
        self.o = call_with_params(
            HDFWriterPart, name="m", mri="BLOCK-HDF5")
        list(self.o.create_attribute_models())
        self.process.start()

    def test_configure(self):
        params = MagicMock()
        energy = LineGenerator("energy", "kEv", 13.0, 15.2, 2)
        spiral = SpiralGenerator(
            ["x", "y"], ["mm", "mm"], [0., 0.], 5., scale=2.0)
        params.generator = CompoundGenerator([energy, spiral], [], [], 0.1)
        params.fileDir = "/tmp"
        params.formatName = "xspress3"
        params.fileTemplate = "thing-%s.h5"
        params.generator.prepare()
        completed_steps = 0
        steps_to_do = 38
        part_info = {
            "DET": [NDArrayDatasetInfo(2)],
            "PANDA": [
                NDAttributeDatasetInfo("I0", "detector", "COUNTER1.COUNTER", 2),
                NDAttributeDatasetInfo("It", "monitor", "COUNTER2.COUNTER", 2),
                NDAttributeDatasetInfo("t1x", "position", "INENC1.VAL", 2)],
            "STAT": [CalculatedNDAttributeDatasetInfo("sum", "StatsTotal")],
        }
        infos = self.o.configure(
            self.context, completed_steps, steps_to_do, part_info, params)
        assert len(infos) == 8
        assert infos[0].name == "xspress3.data"
        assert infos[0].filename == "thing-xspress3.h5"
        assert infos[0].type == "primary"
        assert infos[0].rank == 4
        assert infos[0].path == "/entry/detector/detector"
        assert infos[0].uniqueid == "/entry/NDAttributes/NDArrayUniqueId"

        assert infos[1].name == "xspress3.sum"
        assert infos[1].filename == "thing-xspress3.h5"
        assert infos[1].type == "secondary"
        assert infos[1].rank == 4
        assert infos[1].path == "/entry/sum/sum"
        assert infos[1].uniqueid == "/entry/NDAttributes/NDArrayUniqueId"

        assert infos[2].name == "I0.data"
        assert infos[2].filename == "thing-xspress3.h5"
        assert infos[2].type == "primary"
        assert infos[2].rank == 4
        assert infos[2].path == "/entry/I0/I0"
        assert infos[2].uniqueid == "/entry/NDAttributes/NDArrayUniqueId"

        assert infos[3].name == "It.data"
        assert infos[3].filename == "thing-xspress3.h5"
        assert infos[3].type == "monitor"
        assert infos[3].rank == 4
        assert infos[3].path == "/entry/It/It"
        assert infos[3].uniqueid == "/entry/NDAttributes/NDArrayUniqueId"

        assert infos[4].name == "t1x.value"
        assert infos[4].filename == "thing-xspress3.h5"
        assert infos[4].type == "position_value"
        assert infos[4].rank == 4
        assert infos[4].path == "/entry/t1x/t1x"
        assert infos[4].uniqueid == "/entry/NDAttributes/NDArrayUniqueId"

        assert infos[5].name == "energy.value_set"
        assert infos[5].filename == "thing-xspress3.h5"
        assert infos[5].type == "position_set"
        assert infos[5].rank == 1
        assert infos[5].path == "/entry/detector/energy_set"
        assert infos[5].uniqueid == ""

        assert infos[6].name == "x.value_set"
        assert infos[6].filename == "thing-xspress3.h5"
        assert infos[6].type == "position_set"
        assert infos[6].rank == 1
        assert infos[6].path == "/entry/detector/x_set"
        assert infos[6].uniqueid == ""

        assert infos[7].name == "y.value_set"
        assert infos[7].filename == "thing-xspress3.h5"
        assert infos[7].type == "position_set"
        assert infos[7].rank == 1
        assert infos[7].path == "/entry/detector/y_set"
        assert infos[7].uniqueid == ""

        expected_xml_filename = "/tmp/BLOCK-HDF5-layout.xml"
        # Need to wait for the spawned mock start call to run
        self.o.start_future.result()
        assert self.child.handled_requests.mock_calls == [
            call.put('positionMode', True),
            call.put('arrayCounter', 0),
            call.put('dimAttDatasets', True),
            call.put('enableCallbacks', True),
            call.put('fileName', 'xspress3'),
            call.put('filePath', '/tmp/'),
            call.put('fileTemplate', '%sthing-%s.h5'),
            call.put('fileWriteMode', 'Stream'),
            call.put('lazyOpen', True),
            call.put('positionMode', True),
            call.put('swmrMode', True),
            call.put('extraDimSize3', 1),
            call.put('extraDimSize4', 1),
            call.put('extraDimSize5', 1),
            call.put('extraDimSize6', 1),
            call.put('extraDimSize7', 1),
            call.put('extraDimSize8', 1),
            call.put('extraDimSize9', 1),
            call.put('extraDimSizeN', 20),
            call.put('extraDimSizeX', 2),
            call.put('extraDimSizeY', 1),
            call.put('numExtraDims', 1),
            call.put('posNameDim3', ''),
            call.put('posNameDim4', ''),
            call.put('posNameDim5', ''),
            call.put('posNameDim6', ''),
            call.put('posNameDim7', ''),
            call.put('posNameDim8', ''),
            call.put('posNameDim9', ''),
            call.put('posNameDimN', 'd1'),
            call.put('posNameDimX', 'd0'),
            call.put('posNameDimY', ''),
            call.put('flushAttrPerNFrames', 10.0),
            call.put('flushDataPerNFrames', 10.0),
            call.put('xml', expected_xml_filename),
            call.put('numCapture', 0),
            call.post('start')]
        expected_xml = """<?xml version="1.0" ?>
<hdf5_layout>
<group name="entry">
<attribute name="NX_class" source="constant" type="string" value="NXentry" />
<group name="detector">
<attribute name="signal" source="constant" type="string" value="detector" />
<attribute name="axes" source="constant" type="string" value="energy_set,.,.,." />
<attribute name="NX_class" source="constant" type="string" value="NXdata" />
<attribute name="energy_set_indices" source="constant" type="string" value="0" />
<dataset name="energy_set" source="constant" type="float" value="13,15.2">
<attribute name="units" source="constant" type="string" value="kEv" />
</dataset>
<attribute name="x_set_indices" source="constant" type="string" value="1" />
<dataset name="x_set" source="constant" type="float" value="0.473264298891,-1.28806365331,-1.11933765723,0.721339144968,2.26130106714,2.3717213098,1.08574712174,-0.863941392256,-2.59791589857,-3.46951769442,-3.22399679412,-1.98374931946,-0.132541097885,1.83482458567,3.45008680308,4.36998121172,4.42670524204,3.63379270355,2.15784413199,0.269311496406">
<attribute name="units" source="constant" type="string" value="mm" />
</dataset>
<attribute name="y_set_indices" source="constant" type="string" value="1" />
<dataset name="y_set" source="constant" type="float" value="-0.64237113553,-0.500750778455,1.38930992616,1.98393756064,0.784917470231,-1.17377831157,-2.66405897615,-2.9669684623,-2.01825893141,-0.24129368636,1.72477821509,3.27215424484,3.98722048131,3.71781556747,2.5610299588,0.799047653518,-1.18858453138,-3.01284626565,-4.34725663835,-4.9755042398">
<attribute name="units" source="constant" type="string" value="mm" />
</dataset>
<dataset det_default="true" name="detector" source="detector">
<attribute name="NX_class" source="constant" type="string" value="SDS" />
</dataset>
</group>
<group name="sum">
<attribute name="signal" source="constant" type="string" value="sum" />
<attribute name="axes" source="constant" type="string" value="energy_set,.,.,." />
<attribute name="NX_class" source="constant" type="string" value="NXdata" />
<attribute name="energy_set_indices" source="constant" type="string" value="0" />
<hardlink name="energy_set" target="/entry/detector/energy_set" />
<attribute name="x_set_indices" source="constant" type="string" value="1" />
<hardlink name="x_set" target="/entry/detector/x_set" />
<attribute name="y_set_indices" source="constant" type="string" value="1" />
<hardlink name="y_set" target="/entry/detector/y_set" />
<dataset name="sum" ndattribute="StatsTotal" source="ndattribute" />
</group>
<group name="I0">
<attribute name="signal" source="constant" type="string" value="I0" />
<attribute name="axes" source="constant" type="string" value="energy_set,.,.,." />
<attribute name="NX_class" source="constant" type="string" value="NXdata" />
<attribute name="energy_set_indices" source="constant" type="string" value="0" />
<hardlink name="energy_set" target="/entry/detector/energy_set" />
<attribute name="x_set_indices" source="constant" type="string" value="1" />
<hardlink name="x_set" target="/entry/detector/x_set" />
<attribute name="y_set_indices" source="constant" type="string" value="1" />
<hardlink name="y_set" target="/entry/detector/y_set" />
<dataset name="I0" ndattribute="COUNTER1.COUNTER" source="ndattribute" />
</group>
<group name="It">
<attribute name="signal" source="constant" type="string" value="It" />
<attribute name="axes" source="constant" type="string" value="energy_set,.,.,." />
<attribute name="NX_class" source="constant" type="string" value="NXdata" />
<attribute name="energy_set_indices" source="constant" type="string" value="0" />
<hardlink name="energy_set" target="/entry/detector/energy_set" />
<attribute name="x_set_indices" source="constant" type="string" value="1" />
<hardlink name="x_set" target="/entry/detector/x_set" />
<attribute name="y_set_indices" source="constant" type="string" value="1" />
<hardlink name="y_set" target="/entry/detector/y_set" />
<dataset name="It" ndattribute="COUNTER2.COUNTER" source="ndattribute" />
</group>
<group name="t1x">
<attribute name="signal" source="constant" type="string" value="t1x" />
<attribute name="axes" source="constant" type="string" value="energy_set,.,.,." />
<attribute name="NX_class" source="constant" type="string" value="NXdata" />
<attribute name="energy_set_indices" source="constant" type="string" value="0" />
<hardlink name="energy_set" target="/entry/detector/energy_set" />
<attribute name="x_set_indices" source="constant" type="string" value="1" />
<hardlink name="x_set" target="/entry/detector/x_set" />
<attribute name="y_set_indices" source="constant" type="string" value="1" />
<hardlink name="y_set" target="/entry/detector/y_set" />
<dataset name="t1x" ndattribute="INENC1.VAL" source="ndattribute" />
</group>
<group name="NDAttributes" ndattr_default="true">
<attribute name="NX_class" source="constant" type="string" value="NXcollection" />
</group>
</group>
</hdf5_layout>"""
        actual_xml = open(expected_xml_filename).read().replace(">", ">\n")
        assert actual_xml.splitlines() == expected_xml.splitlines()

    def test_run(self):
        update = MagicMock()
        self.o.done_when_reaches = 38
        self.o.completed_offset = 0
        # Say that we're getting the first frame
        self.o.array_future = Future(None)
        self.o.array_future.set_result(None)
        # run waits for this value
        self.child.parts["uniqueId"].attr.set_value(self.o.done_when_reaches)
        self.o.run(self.context, update)
        assert self.child.handled_requests.mock_calls == []
        assert update.mock_calls == [call(38, self.o)]

    def test_seek(self):
        completed_steps = 4
        steps_to_do = 3
        part_infos = {ANY: [UniqueIdInfo(10)]}
        self.o.seek(self.context, completed_steps, steps_to_do, part_infos)
        assert self.child.handled_requests.mock_calls == [
            call.put('arrayCounter', 0)]
        assert self.o.done_when_reaches == 13

    def test_post_run_idle(self):
        # Say that we've returned from start
        self.o.start_future = Future(None)
        self.o.start_future.set_result(None)
        fname = "/tmp/test_filename"
        with open(fname, "w") as f:
            f.write("thing")
        assert os.path.isfile(fname)
        self.o.layout_filename = fname
        self.o.post_run_idle(self.context)
        assert self.child.handled_requests.mock_calls == []
        assert not os.path.isfile(fname)
