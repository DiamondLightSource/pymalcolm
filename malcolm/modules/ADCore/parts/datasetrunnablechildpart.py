from annotypes import add_call_types, Any

from malcolm.core import APartName
from malcolm.modules.scanning.parts import RunnableChildPart, AMri, \
    AInitialVisibility
from malcolm.modules import scanning
from ..infos import DatasetProducedInfo


class DatasetRunnableChildPart(RunnableChildPart):
    """Part controlling a configure/run child Block with a dataset table"""

    def __init__(self, name, mri, initial_visibility=False):
        # type: (APartName, AMri, AInitialVisibility) -> None
        super(DatasetRunnableChildPart, self).__init__(
            name, mri, initial_visibility, ignore_configure_args="formatName")

    @add_call_types
    def validate(self,
                 context,  # type: scanning.hooks.AContext
                 **kwargs  # type: **Any
                 ):
        # type: (...) -> scanning.hooks.UParameterTweakInfos
        child = context.block_view(self.mri)
        # Add formatName in if the child wants it
        if "formatName" in child.configure.takes.elements:
            kwargs["formatName"] = self.name
        return super(DatasetRunnableChildPart, self).validate(context, **kwargs)

    @add_call_types
    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  **kwargs  # type: **Any
                  ):
        # type: (...) -> scanning.hooks.UInfos
        child = context.block_view(self.mri)
        # Add formatName in if the child wants it
        if "formatName" in child.configure.takes.elements:
            kwargs["formatName"] = self.name
        # Run the configure command
        super(DatasetRunnableChildPart, self).configure(context, **kwargs)
        info_list = []
        # Report back any datasets the child has to our parent
        if hasattr(child, "datasets"):
            datasets_table = child.datasets.value
            for row in datasets_table.rows():
                info_list.append(DatasetProducedInfo(*row))
        return info_list
