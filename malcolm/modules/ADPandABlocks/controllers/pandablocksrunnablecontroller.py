from annotypes import Anno

from malcolm.core import snake_to_camel
from malcolm.modules.ADCore.includes import adbase_parts
from malcolm.modules.ADCore.util import AttributeDatasetType
from malcolm.modules.builtin.controllers import StatefulController
from malcolm.modules.builtin.parts import StringPart, ChoicePart
from malcolm.modules.pandablocks.controllers import \
    PandABlocksManagerController, AMri, AConfigDir, AHostname, APort, \
    AInitialDesign, ADescription, AUseCothread, AUseGit
from malcolm.modules.scanning.controllers import RunnableController
from ..parts import PandABlocksDriverPart, PandABlocksChildPart


with Anno("Prefix for areaDetector records"):
    APrefix = str


class PandABlocksRunnableController(PandABlocksManagerController,
                                    RunnableController):
    def __init__(self,
                 mri,  # type: AMri
                 config_dir,  # type: AConfigDir
                 prefix,  # type: APrefix
                 hostname="localhost",  # type: AHostname
                 port=8888,  # type: APort
                 initial_design="",  # type: AInitialDesign
                 description="",  # type: ADescription
                 use_cothread=True,  # type: AUseCothread
                 use_git=True,  # type: AUseGit
                 ):
        # type: (...) -> None
        super(PandABlocksRunnableController, self).__init__(
            mri, config_dir, hostname, port, initial_design, description,
            use_cothread, use_git)
        self.prefix = prefix

    def _make_child_controller(self, parts, mri):
        # Add some extra parts to determine the dataset name and type for
        # any CAPTURE field part
        new_parts = []
        for existing_part in parts:
            new_parts.append(existing_part)
            if hasattr(existing_part, "field_name") and \
                    existing_part.field_name.endswith(".CAPTURE"):
                # Add capture dataset name and type
                part_name = existing_part.field_name.replace(
                    ".CAPTURE", ".DATASET_NAME")
                attr_name = snake_to_camel(part_name.replace(".", "_"))
                new_parts.append(StringPart(
                    name=attr_name,
                    description="Name of the captured dataset in HDF file",
                    writeable=True))
                # Make a choice part to hold the type of the dataset
                part_name = existing_part.field_name.replace(
                    ".CAPTURE", ".DATASET_TYPE")
                attr_name = snake_to_camel(part_name.replace(".", "_"))
                if "INENC" in mri:
                    initial = "position"
                else:
                    initial = "monitor"
                new_parts.append(ChoicePart(
                    name=attr_name,
                    description="Type of the captured dataset in HDF file",
                    writeable=True, choices=list(AttributeDatasetType),
                    value=initial))
        if mri.endswith("PCAP"):
            cs, ps = adbase_parts(prefix=self.prefix)
            controller = StatefulController(mri=mri)
            for p in new_parts + ps:
                controller.add_part(p)
            for c in cs:
                self.process.add_controller(c)
        else:
            controller = super(PandABlocksRunnableController, self).\
                _make_child_controller(new_parts, mri)
        return controller



    def _make_corresponding_part(self, block_name, mri):
        if block_name == "PCAP":
            part = PandABlocksDriverPart(name=block_name, mri=mri)
        else:
            part = PandABlocksChildPart(
                name=block_name, mri=mri, stateful=False)
        return part
