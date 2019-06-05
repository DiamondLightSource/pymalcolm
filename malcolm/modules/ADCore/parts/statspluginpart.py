import os
from xml.etree import cElementTree as ET

from annotypes import Anno, add_call_types

from malcolm.compat import et_to_string
from malcolm.core import APartName, PartRegistrar
from malcolm.modules import builtin, scanning
from ..infos import CalculatedNDAttributeDatasetInfo, FilePathTranslatorInfo
from ..util import StatisticsName, APartRunsOnWindows

with Anno("Which statistic to capture"):
    AStatsName = StatisticsName
with Anno("Directory to write data to"):
    AFileDir = str

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName


# We will set these attributes on the child block, so don't save them
@builtin.util.no_save(
    "attributesFile", "enableCallbacks", "computeStatistics", "arrayCounter")
class StatsPluginPart(builtin.parts.ChildPart):
    """Part for controlling a `stats_plugin_block` in a Device"""

    def __init__(self,
                 name,                          # type: APartName
                 mri,                           # type: builtin.parts.AMri
                 statistic=StatisticsName.SUM,  # type: AStatsName
                 runs_on_windows=False,         # type: APartRunsOnWindows
                 ):
        # type: (...) -> None
        super(StatsPluginPart, self).__init__(name, mri)
        self.statistic = statistic
        # The NDAttributes file we write to say what to capture
        self.attributes_filename = None  # type: str
        self.runs_on_windows = runs_on_windows

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(StatsPluginPart, self).setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ReportStatusHook, self.report_status)
        registrar.hook(scanning.hooks.ConfigureHook, self.configure)

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
    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  part_info,  # type: scanning.hooks.APartInfo
                  fileDir  # type: scanning.hooks.AFileDir
                  ):
        # type: (...) -> None
        child = context.block_view(self.mri)
        fs = child.put_attribute_values_async(dict(
            enableCallbacks=True,
            computeStatistics=True))
        xml = self._make_attributes_xml()
        self.attributes_filename = os.path.join(
            fileDir, "%s-attributes.xml" % self.mri)
        with open(self.attributes_filename, "w") as f:
            f.write(xml)
        attributes_filename = self.attributes_filename
        if self.runs_on_windows:
            attributes_filename = FilePathTranslatorInfo.translate_filepath(
                part_info, self.attributes_filename)
        fs.append(
            child.attributesFile.put_value_async(attributes_filename))
        context.wait_all_futures(fs)

    @add_call_types
    def reset(self, context):
        # type: (scanning.hooks.AContext) -> None
        super(StatsPluginPart, self).reset(context)
        # Delete the attribute XML file
        if self.attributes_filename and os.path.isfile(
                self.attributes_filename):
            os.remove(self.attributes_filename)
            child = context.block_view(self.mri)
            child.attributesFile.put_value("")
