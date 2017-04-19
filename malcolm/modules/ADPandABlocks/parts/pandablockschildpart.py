import re

from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.ADCore.infos import NDAttributeDatasetInfo
from malcolm.modules.builtin.parts import ChildPart


class PandABlocksChildPart(ChildPart):
    # Stored futures
    start_future = None

    def _is_capture_field(self, child, attr_name):
        if attr_name.endswith("Capture"):
            attr = child[attr_name]
            if attr.value.lower() != "no":
                return True

    def _dataset_info(self, child, attr_name):
        dataset_name_attr = attr_name + "DatasetName"
        dataset_type_attr = attr_name + "DatasetType"
        if dataset_name_attr in child and dataset_type_attr in child:
            dataset_name = child[dataset_name_attr].value
            if dataset_name == "":
                return
            assert "." not in dataset_name, \
                "Dataset name should not contain '.'"
            dataset_type = child[dataset_type_attr].value
            uppercase_attr = re.sub("([A-Z])", r"_\1", attr_name).upper()
            return NDAttributeDatasetInfo(
                name=dataset_name,
                type=dataset_type,
                rank=2,
                attr="%s.%s" % (self.name, uppercase_attr))

    @RunnableController.ReportStatus
    def report_configuration(self, context):
        ret = []
        child = context.block_view(self.params.mri)
        for attr_name in child:
            if self._is_capture_field(child, attr_name):
                dataset_info = self._dataset_info(
                    child, attr_name[:-len("Capture")])
                if dataset_info:
                    ret.append(dataset_info)
        return ret
