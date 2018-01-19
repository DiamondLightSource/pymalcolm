from malcolm.modules import ADCore
from .pandablockschildpart import PandABlocksChildPart


class PandABlocksDriverPart(ADCore.parts.DetectorDriverPart,
                            PandABlocksChildPart):
    def __init__(self, name, mri):
        # type: (ADCore.parts.APartName, ADCore.parts.AMri) -> None
        super(PandABlocksDriverPart, self).__init__(
            name, mri, main_dataset_useful=False)
