import re

from malcolm.parts.builtin.childpart import ChildPart
from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.ADCore.hdfwriterpart import DatasetSourceInfo


class PandABoxChildPart(ChildPart):
    # Stored futures
    start_future = None

    def _is_capture_field(self, attr_name):
        if attr_name.endswith("Capture"):
            attr = self.child[attr_name]
            if attr.value.lower() != "no":
                return True

    def _dataset_info(self, attr_name):
        dataset_attr_name = attr_name + "DatasetName"
        if dataset_attr_name in self.child:
            dataset_name = self.child[dataset_attr_name].value
            if dataset_name == "":
                return
            elif "INENC" in self.params.mri:
                dataset_type = "position_value"
            else:
                dataset_type = "monitor"
            assert "." not in dataset_name, \
                "Dataset name should not contain '.'"

            uppercase_attr = re.sub("([A-Z])", r"_\1", attr_name).upper()
            return DatasetSourceInfo(
                name="%s.value" % dataset_name,
                type=dataset_type,
                rank=0,
                attr=uppercase_attr)

    @RunnableController.ReportStatus
    def report_configuration(self, _):
        ret = []
        for attr_name in self.child:
            if self._is_capture_field(attr_name):
                dataset_info = self._dataset_info(attr_name[:-len("Capture")])
                if dataset_info:
                    ret.append(dataset_info)
        return ret
