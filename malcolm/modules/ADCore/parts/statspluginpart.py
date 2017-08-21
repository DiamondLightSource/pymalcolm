import os
from xml.etree import cElementTree as ET

from malcolm.compat import et_to_string, OrderedDict
from malcolm.core import REQUIRED, method_takes, method_also_takes
from malcolm.modules.ADCore.infos import CalculatedNDAttributeDatasetInfo
from malcolm.modules.builtin.parts import StatefulChildPart
from malcolm.modules.builtin.vmetas import StringMeta, ChoiceMeta
from malcolm.modules.scanning.controllers import RunnableController


statistics = OrderedDict()

statistics["min"] = "MIN_VALUE"  # Minimum counts in any element
statistics["min_x"] = "MIN_X"  # X position of minimum counts
statistics["min_y"] = "MIN_Y"  # Y position of minimum counts
statistics["max"] = "MAX_VALUE"  # Maximum counts in any element
statistics["max_x"] = "MAX_X"  # X position of maximum counts
statistics["max_y"] = "MAX_Y"  # Y position of maximum counts
statistics["mean"] = "MEAN_VALUE"  # Mean counts of all elements
statistics["sigma"] = "SIGMA_VALUE"  # Sigma of all elements
statistics["sum"] = "TOTAL"  # Sum of all elements
statistics["net"] = "NET"  # Sum of all elements not in background region


@method_also_takes(
    "statistic", ChoiceMeta("Which statistic to capture", statistics), "sum")
class StatsPluginPart(StatefulChildPart):
    """Part for controlling a `stats_plugin_block` in a Device"""
    # The NDAttributes file we write to say what to capture
    attributes_filename = None

    @RunnableController.ReportStatus
    def report_info(self, _):
        statistic, _, attr = self._get_statistic_source_attr()
        return [CalculatedNDAttributeDatasetInfo(name=statistic, attr=attr)]

    def _get_statistic_source_attr(self):
        statistic = self.params.statistic
        source = statistics[statistic]
        attr = "STATS_%s" % source
        return statistic, source, attr

    def _make_attributes_xml(self):
        # Make a root element with an NXEntry
        root_el = ET.Element("Attributes")
        statistic, source, attr = self._get_statistic_source_attr()
        ET.SubElement(
            root_el, "Attribute", addr="0", datatype="DOUBLE", type="PARAM",
            description="%s of the array" % statistic.title(), name=attr,
            source=source)
        xml = et_to_string(root_el)
        return xml

    @RunnableController.Configure
    @method_takes(
        "fileDir", StringMeta("File directory to write data to"), REQUIRED)
    def configure(self, context, completed_steps, steps_to_do, part_info,
                  params):
        child = context.block_view(self.params.mri)
        fs = child.put_attribute_values_async(dict(
            enableCallbacks=True,
            computeStatistics=True))
        xml = self._make_attributes_xml()
        self.attributes_filename = os.path.join(
            params.fileDir, "%s-attributes.xml" % self.params.mri)
        with open(self.attributes_filename, "w") as f:
            f.write(xml)
        fs.append(
            child.attributesFile.put_value_async(self.attributes_filename))
        context.wait_all_futures(fs)

    @RunnableController.PostRunReady
    def post_run_ready(self, context):
        # Delete the attribute XML file
        os.remove(self.attributes_filename)
