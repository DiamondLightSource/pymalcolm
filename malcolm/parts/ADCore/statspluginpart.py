import os
from xml.etree import cElementTree as ET

from malcolm.compat import et_to_string
from malcolm.core import REQUIRED, method_takes
from malcolm.core.vmetas import StringMeta
from malcolm.parts.builtin.childpart import ChildPart
from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.ADCore.hdfwriterpart import CalculatedNDAttributeDatasetInfo


class StatsPluginPart(ChildPart):

    @RunnableController.ReportStatus
    def report_info(self, _):
        return [CalculatedNDAttributeDatasetInfo(name="sum", attr="StatsTotal")]

    def _make_attributes_xml(self):
        # Make a root element with an NXEntry
        root_el = ET.Element("Attributes")
        ET.SubElement(
            root_el, "Attribute", addr="0", datatype="DOUBLE", type="PARAM",
            description="Sum of the array", name="StatsTotal", source="TOTAL",
        )
        xml = et_to_string(root_el)
        return xml

    @RunnableController.Configure
    @method_takes(
        "filePath", StringMeta("File path to write data to"), REQUIRED)
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        file_dir, filename = params.filePath.rsplit(os.sep, 1)
        fs = task.put_many_async(self.child, dict(
            enableCallbacks=True,
            computeStatistics=True))
        xml = self._make_attributes_xml()
        attributes_filename = os.path.join(
            file_dir, "%s-attributes.xml" % self.params.mri)
        open(attributes_filename, "w").write(xml)
        fs += task.put_async(self.child["attributesFile"], attributes_filename)
        task.wait_all(fs)
