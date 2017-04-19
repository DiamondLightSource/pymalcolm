from malcolm.core import method_also_takes, REQUIRED, call_with_params, \
    snake_to_camel
from malcolm.modules.ADCore.includes import adbase_parts
from malcolm.modules.ADCore.infos import attribute_dataset_types
from malcolm.modules.ADPandABlocks.parts import PandABlocksDriverPart, \
    PandABlocksChildPart
from malcolm.modules.builtin.controllers import StatefulController
from malcolm.modules.builtin.parts import StringPart, ChoicePart
from malcolm.modules.builtin.vmetas import StringMeta, StringArrayMeta
from malcolm.modules.pandablocks.controllers import PandABlocksManagerController
from malcolm.modules.scanning.controllers import RunnableController


@method_also_takes(
    "areaDetectorPrefix", StringMeta(
        "Prefix for areaDetector records"), REQUIRED,
    "axesToMove", StringArrayMeta("Default value for configure() axesToMove"),
    []
)
class PandABlocksRunnableController(PandABlocksManagerController,
                                    RunnableController):
    def _make_child_controller(self, parts, mri):
        # Add some extra parts to determine the dataset name and type for
        # any CAPTURE field part
        new_parts = []
        for existing_part in parts:
            new_parts.append(existing_part)
            if existing_part.name.endswith(".CAPTURE"):
                # Add capture dataset name and type
                part_name = existing_part.name.replace(
                    ".CAPTURE", ".DATASET_NAME")
                attr_name = snake_to_camel(part_name.replace(".", "_"))
                new_parts.append(call_with_params(
                    StringPart, name=attr_name, widget="textinput",
                    description="Name of the captured dataset in HDF file",
                    writeable=True, config=True))
                # Make a choice part to hold the type of the dataset
                part_name = existing_part.name.replace(
                    ".CAPTURE", ".DATASET_TYPE")
                attr_name = snake_to_camel(part_name.replace(".", "_"))
                if "INENC" in mri:
                    initial = "position"
                else:
                    initial = "monitor"
                new_parts.append(call_with_params(
                    ChoicePart, name=attr_name, widget="combo",
                    description="Type of the captured dataset in HDF file",
                    writeable=True, choices=attribute_dataset_types,
                    initialValue=initial))
        if mri.endswith("PCAP"):
            new_parts += call_with_params(
                adbase_parts, self.process,
                prefix=self.params.areaDetectorPrefix)
            controller = call_with_params(
                StatefulController, self.process, new_parts, mri=mri)
        else:
            controller = super(PandABlocksRunnableController, self).\
                _make_child_controller(new_parts, mri)
        return controller

    def _make_corresponding_part(self, block_name, mri):
        if block_name == "PCAP":
            part_cls = PandABlocksDriverPart
        else:
            part_cls = PandABlocksChildPart
        part = call_with_params(part_cls, name=block_name, mri=mri)
        return part
