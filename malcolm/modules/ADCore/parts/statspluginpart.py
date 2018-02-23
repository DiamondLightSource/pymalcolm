import os
from xml.etree import cElementTree as ET

from annotypes import Anno, add_call_types

from malcolm.compat import et_to_string
from malcolm.core import APartName, Hook
from malcolm.modules import builtin, scanning
from ..infos import CalculatedNDAttributeDatasetInfo
from ..util import StatisticsName

with Anno("Which statistic to capture"):
    AStatisticsName = StatisticsName
with Anno("Directory to write data to"):
    AFileDir = str


class StatsPluginPart(builtin.parts.ChildPart):
    """Part for controlling a `stats_plugin_block` in a Device"""

    def __init__(self, name, mri, statistic=StatisticsName.SUM):
        # type: (APartName, builtin.parts.AMri, AStatisticsName) -> None
        super(StatsPluginPart, self).__init__(name, mri)
        self.statistic = statistic
        # The NDAttributes file we write to say what to capture
        self.attributes_filename = None  # type: str
        # Hooks
        self.register_hooked(scanning.hooks.ReportStatusHook,
                             self.report_status)
        self.register_hooked(scanning.hooks.ConfigureHook, self.configure)
        self.register_hooked(scanning.hooks.PostRunReadyHook,
                             self.post_run_ready)

    @add_call_types
    def report_status(self):
        # type: () -> scanning.hooks.UInfos
        return [CalculatedNDAttributeDatasetInfo(
            name=self.statistic.name.lower(), attr=self.statistic_attr())]

    def statistic_attr(self):
        # type: () -> str
        return "STATS_%s" % self.statistic.value

    def _make_attributes_xml(self):
        # Make a root element with an NXEntry
        root_el = ET.Element("Attributes")
        ET.SubElement(
            root_el, "Attribute", addr="0", datatype="DOUBLE", type="PARAM",
            description="%s of the array" % self.statistic.name.title(),
            name=self.statistic_attr(), source=self.statistic.value)
        xml = et_to_string(root_el)
        return xml

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def configure(self, context, fileDir):
        # type: (scanning.hooks.AContext, AFileDir) -> None
        child = context.block_view(self.mri)
        fs = child.put_attribute_values_async(dict(
            enableCallbacks=True,
            computeStatistics=True))
        xml = self._make_attributes_xml()
        self.attributes_filename = os.path.join(
            fileDir, "%s-attributes.xml" % self.mri)
        with open(self.attributes_filename, "w") as f:
            f.write(xml)
        fs.append(
            child.attributesFile.put_value_async(self.attributes_filename))
        context.wait_all_futures(fs)

    @add_call_types
    def post_run_ready(self):
        # type: () -> None
        # Delete the attribute XML file
        os.remove(self.attributes_filename)
