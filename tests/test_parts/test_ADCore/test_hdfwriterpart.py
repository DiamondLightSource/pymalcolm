import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, MagicMock, call, ANY

from malcolm.parts.ADCore.hdfwriterpart import HDFWriterPart, \
    NDArrayDatasetInfo, CalculatedNDAttributeDatasetInfo

from scanpointgenerator import LineGenerator, CompoundGenerator, SpiralGenerator


class TestHDFWriterPart(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.process = MagicMock()
        self.child = MagicMock()

        def getitem(name):
            return name

        self.child.__getitem__.side_effect = getitem

        self.params = MagicMock()
        self.params.mri = "BLOCK-HDF5"
        self.process.get_block.return_value = self.child
        self.o = HDFWriterPart(self.process, self.params)
        list(self.o.create_attributes())

    def test_configure(self):
        task = MagicMock()
        params = MagicMock()
        energy = LineGenerator("energy", "kEv", 13.0, 15.2, 2)
        spiral = SpiralGenerator(
            ["x", "y"], ["mm", "mm"], [0., 0.], 5., scale=2.0)
        params.generator = CompoundGenerator([energy, spiral], [], [], 0.1)
        params.fileDir = "/tmp"
        params.formatName = "file"
        params.fileTemplate = "thing-%s.h5"
        params.generator.prepare()
        completed_steps = 0
        steps_to_do = 38
        part_info = {
            "DET": [NDArrayDatasetInfo("xspress3", 2)],
            "STAT": [CalculatedNDAttributeDatasetInfo("sum", "StatsTotal")],
        }
        infos = self.o.configure(
            task, completed_steps, steps_to_do, part_info, params)
        self.assertEqual(len(infos), 5)
        self.assertEquals(infos[0].name, "xspress3.data")
        self.assertEquals(infos[0].filename, "thing-file.h5")
        self.assertEquals(infos[0].type, "primary")
        self.assertEquals(infos[0].rank, 4)
        self.assertEquals(infos[0].path, "/entry/detector/detector")
        self.assertEquals(infos[0].uniqueid,
                          "/entry/NDAttributes/NDArrayUniqueId")
        self.assertEquals(infos[1].name, "xspress3.sum")
        self.assertEquals(infos[1].filename, "thing-file.h5")
        self.assertEquals(infos[1].type, "secondary")
        self.assertEquals(infos[1].rank, 4)
        self.assertEquals(infos[1].path, "/entry/sum/sum")
        self.assertEquals(infos[1].uniqueid,
                          "/entry/NDAttributes/NDArrayUniqueId")
        self.assertEquals(infos[2].name, "energy.value_set")
        self.assertEquals(infos[2].filename, "thing-file.h5")
        self.assertEquals(infos[2].type, "position_set")
        self.assertEquals(infos[2].rank, 1)
        self.assertEquals(infos[2].path, "/entry/detector/energy_set")
        self.assertEquals(infos[2].uniqueid, "")
        self.assertEquals(infos[3].name, "x.value_set")
        self.assertEquals(infos[3].filename, "thing-file.h5")
        self.assertEquals(infos[3].type, "position_set")
        self.assertEquals(infos[3].rank, 1)
        self.assertEquals(infos[3].path, "/entry/detector/x_set")
        self.assertEquals(infos[3].uniqueid, "")
        self.assertEquals(infos[4].name, "y.value_set")
        self.assertEquals(infos[4].filename, "thing-file.h5")
        self.assertEquals(infos[4].type, "position_set")
        self.assertEquals(infos[4].rank, 1)
        self.assertEquals(infos[4].path, "/entry/detector/y_set")
        self.assertEquals(infos[4].uniqueid, "")
        self.assertEqual(task.put.call_args_list, [
            call(self.child["positionMode"], True),
            call(self.child["numCapture"], 0),
            call('flushDataPerNFrames', 10.0),
            call('flushAttrPerNFrames', 10.0)])
        self.assertEqual(task.put_many_async.call_count, 2)
        self.assertEqual(task.put_many_async.call_args_list[0],
                         call(self.child, dict(
                             enableCallbacks=True,
                             fileWriteMode="Stream",
                             swmrMode=True,
                             positionMode=True,
                             dimAttDatasets=True,
                             lazyOpen=True,
                             arrayCounter=0,
                             filePath="/tmp/",
                             fileName="file",
                             fileTemplate="%sthing-%s.h5")))
        self.assertEqual(task.put_many_async.call_args_list[1],
                         call(self.child, dict(
                             numExtraDims=1,
                             posNameDimN="d1",
                             extraDimSizeN=20,
                             posNameDimX="d0",
                             extraDimSizeX=2,
                             posNameDimY="",
                             extraDimSizeY=1,
                             posNameDim3="",
                             extraDimSize3=1,
                             posNameDim4="",
                             extraDimSize4=1,
                             posNameDim5="",
                             extraDimSize5=1,
                             posNameDim6="",
                             extraDimSize6=1,
                             posNameDim7="",
                             extraDimSize7=1,
                             posNameDim8="",
                             extraDimSize8=1,
                             posNameDim9="",
                             extraDimSize9=1)))
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
<group name="NDAttributes" ndattr_default="true">
<attribute name="NX_class" source="constant" type="string" value="NXcollection" />
</group>
</group>
</hdf5_layout>"""
        expected_filename = "/tmp/BLOCK-HDF5-layout.xml"
        self.assertEqual(
            task.put_async.call_args_list[0][0][1], expected_filename)
        actual_xml = open(expected_filename).read().replace(">", ">\n")
        self.assertEqual(actual_xml.splitlines(), expected_xml.splitlines())

    def test_run(self):
        task = MagicMock()
        update = MagicMock()
        self.o.done_when_reaches = 38
        self.o.run(task, update)
        task.subscribe.assert_called_once_with(
            self.child["uniqueId"], update, self.o)
        task.when_matches.assert_called_once_with(
            self.child["uniqueId"], 38)

    def test_post_run(self):
        self.o.start_future = MagicMock()
        fname = "/tmp/test_filename"
        with open(fname, "w") as f:
            f.write("thing")
        assert os.path.isfile(fname)
        self.o.layout_filename = fname
        task = MagicMock()
        self.o.post_run_idle(task)
        task.wait_all.assert_called_once_with(self.o.start_future)
        assert not os.path.isfile(fname)


if __name__ == "__main__":
    unittest.main(verbosity=2)
