import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, MagicMock, call, ANY

from malcolm.parts.ADCore.hdfwriterpart import HDFWriterPart, DatasetSourceInfo

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
        self.process.get_block.return_value = self.child
        self.o = HDFWriterPart(self.process, self.params)
        list(self.o.create_attributes())

    def test_init(self):
        self.process.get_block.assert_called_once_with(self.params.child)
        self.assertEqual(self.o.child, self.child)

    def test_configure(self):
        task = MagicMock()
        params = MagicMock()
        energy = LineGenerator("energy", "kEv", 13.0, 15.2, 2)
        spiral = SpiralGenerator(["x", "y"], "mm", [0., 0.], 5., scale=2.0)
        params.generator = CompoundGenerator([energy, spiral], [], [])
        params.filePath = "/path/to/file.h5"
        completed_steps = 0
        steps_to_do = 38
        part_info = {
            "DET": [DatasetSourceInfo("detector", "primary")],
            "STAT": [DatasetSourceInfo("StatsTotal", "additional")],
        }
        self.o.configure(task, completed_steps, steps_to_do, part_info, params)
        self.assertEqual(task.put.call_args_list, [
            call(self.child["positionMode"], True),
            call(self.child["numCapture"], 0)])
        self.assertEqual(task.put_async.call_count, 4)
        self.assertEqual(task.put_async.call_args_list[0], call({
                self.child["enableCallbacks"]: True,
                self.child["fileWriteMode"]: "Stream",
                self.child["swmrMode"]: True,
                self.child["positionMode"]: True,
                self.child["dimAttDatasets"]: True,
                self.child["lazyOpen"]: True,
                self.child["arrayCounter"]: 0,
        }))
        self.assertEqual(task.put_async.call_args_list[1], call({
                self.child["filePath"]: "/path/to/",
                self.child["fileName"]: "file.h5",
                self.child["fileTemplate"]: "%s%s"}))
        self.assertEqual(task.put_async.call_args_list[2], call({
                self.child["numExtraDims"]: 1,
                self.child["posNameDimN"]: "x_y_Spiral_index",
                self.child["extraDimSizeN"]: 19,
                self.child["posNameDimX"]: "energy_index",
                self.child["extraDimSizeX"]: 2,
                self.child["posNameDimY"]: "",
                self.child["extraDimSizeY"]: 1,
                self.child["posNameDim3"]: "",
                self.child["extraDimSize3"]: 1,
                self.child["posNameDim4"]: "",
                self.child["extraDimSize4"]: 1,
                self.child["posNameDim5"]: "",
                self.child["extraDimSize5"]: 1,
                self.child["posNameDim6"]: "",
                self.child["extraDimSize6"]: 1,
                self.child["posNameDim7"]: "",
                self.child["extraDimSize7"]: 1,
                self.child["posNameDim8"]: "",
                self.child["extraDimSize8"]: 1,
                self.child["posNameDim9"]: "",
                self.child["extraDimSize9"]: 1}))
        expected_xml = """<?xml version="1.0" ?>
<hdf5_layout>
<group name="entry">
<attribute name="NX_class" source="constant" type="string" value="NXentry" />
<group name="detector">
<attribute name="signal" source="constant" type="string" value="detector" />
<attribute name="axes" source="constant" type="string" value="energy_demand,x_y_Spiral_demand,.,." />
<attribute name="NX_class" source="constant" type="string" value="NXdata" />
<attribute name="energy_demand_indices" source="constant" type="string" value="0" />
<attribute name="x_y_Spiral_demand_indices" source="constant" type="string" value="1" />
<dataset name="energy_demand" ndattribute="energy" source="ndattribute">
<attribute name="units" source="constant" type="string" value="kEv" />
</dataset>
<dataset name="x_demand" ndattribute="x" source="ndattribute">
<attribute name="units" source="constant" type="string" value="mm" />
</dataset>
<dataset name="y_demand" ndattribute="y" source="ndattribute">
<attribute name="units" source="constant" type="string" value="mm" />
</dataset>
<dataset det_default="true" name="detector" source="detector">
<attribute name="NX_class" source="constant" type="string" value="SDS" />
</dataset>
</group>
<group name="StatsTotal">
<attribute name="signal" source="constant" type="string" value="StatsTotal" />
<attribute name="axes" source="constant" type="string" value="energy_demand,x_y_Spiral_demand,.,." />
<attribute name="NX_class" source="constant" type="string" value="NXdata" />
<attribute name="energy_demand_indices" source="constant" type="string" value="0" />
<attribute name="x_y_Spiral_demand_indices" source="constant" type="string" value="1" />
<hardlink name="energy_demand" target="/entry/detector/energy_demand" />
<hardlink name="x_demand" target="/entry/detector/x_demand" />
<hardlink name="y_demand" target="/entry/detector/y_demand" />
<dataset name="StatsTotal" ndattribute="StatsTotal" source="ndattribute" />
</group>
<group name="NDAttributes" ndattr_default="true">
<attribute name="NX_class" source="constant" type="string" value="NXcollection" />
</group>
</group>
</hdf5_layout>"""
        self.assertEqual(
            task.put_async.call_args_list[3][0][1].replace(">", ">\n").splitlines(),
            expected_xml.splitlines())

    def test_run(self):
        task = MagicMock()
        update = MagicMock()
        self.o.done_when_reaches = 38
        self.o.run(task, update)
        task.subscribe.assert_called_once_with(
            self.child["uniqueId"], update)
        task.when_matches.assert_called_once_with(
            self.child["uniqueId"], 38)
        task.unsubscribe.assert_called_once_with(
            task.subscribe.return_value)

    def test_post_run(self):
        self.o.start_future = MagicMock()
        task = MagicMock()
        self.o.wait_until_closed(task, more_steps=False)
        task.wait_all.assert_called_once_with(self.o.start_future)


if __name__ == "__main__":
    unittest.main(verbosity=2)
