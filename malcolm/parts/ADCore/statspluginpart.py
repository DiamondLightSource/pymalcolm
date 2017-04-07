import os
from xml.etree import cElementTree as ET

from malcolm.compat import et_to_string
from malcolm.controllers.scanning.runnablecontroller import RunnableController
from malcolm.core import REQUIRED, method_takes
from malcolm.infos.ADCore.calculatedndattributedatasetinfo import \
    CalculatedNDAttributeDatasetInfo
from malcolm.parts.builtin import StatefulChildPart
from malcolm.vmetas.builtin import StringMeta


class StatsPluginPart(StatefulChildPart):

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
    def configure(self, context, completed_steps, steps_to_do, part_info,
                  params):
        file_dir, filename = params.filePath.rsplit(os.sep, 1)
        child = context.block_view(self.params.mri)
        fs = child.put_attribute_values(dict(
            enableCallbacks=True,
            computeStatistics=True))
        xml = self._make_attributes_xml()
        attributes_filename = os.path.join(
            file_dir, "%s-attributes.xml" % self.params.mri)
        open(attributes_filename, "w").write(xml)
        child.attributesFile.put_value(attributes_filename)
        context.wait_all_futures(fs)
