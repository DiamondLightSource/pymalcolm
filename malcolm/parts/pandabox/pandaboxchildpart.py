import re

from malcolm.parts.builtin.childpart import ChildPart
from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.ADCore.hdfwriterpart import NDAttributeDatasetInfo


class PandABoxChildPart(ChildPart):
    # Stored futures
    start_future = None

    def _is_capture_field(self, attr_name):
        if attr_name.endswith("Capture"):
            attr = self.child[attr_name]
            if attr.value.lower() != "no":
                return True

    def _dataset_info(self, attr_name):
        dataset_name_attr = attr_name + "DatasetName"
        dataset_type_attr = attr_name + "DatasetType"
        if dataset_name_attr in self.child and dataset_type_attr in self.child:
            dataset_name = self.child[dataset_name_attr].value
            if dataset_name == "":
                return
            assert "." not in dataset_name, \
                "Dataset name should not contain '.'"
            dataset_type = self.child[dataset_type_attr].value
            uppercase_attr = re.sub("([A-Z])", r"_\1", attr_name).upper()
            return NDAttributeDatasetInfo(
                name=dataset_name,
                type=dataset_type,
                rank=2,
                attr="%s.%s" % (self.name, uppercase_attr))

    @RunnableController.ReportStatus
    def report_configuration(self, _):
        ret = []
        for attr_name in self.child:
            if self._is_capture_field(attr_name):
                dataset_info = self._dataset_info(attr_name[:-len("Capture")])
                if dataset_info:
                    ret.append(dataset_info)
        return ret
