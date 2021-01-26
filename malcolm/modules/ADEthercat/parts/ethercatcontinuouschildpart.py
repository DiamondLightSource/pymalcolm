from annotypes import add_call_types

from malcolm.core import BadValueError, Put, Request
from malcolm.modules import builtin
from malcolm.modules.builtin.parts import ChildPart
from malcolm.modules.scanning.hooks import (
    AAxesToMove,
    AbortHook,
    AContext,
    AFileDir,
    AFileTemplate,
    AGenerator,
    ConfigureHook,
    PreConfigureHook,
    UInfos,
)
from malcolm.modules.scanning.infos import DatasetProducedInfo
from malcolm.modules.scanning.util import ADetectorTable


class EthercatContinuousChildPart(ChildPart):
    """Part for controlling a continuous Ethercat block with no progress"""

    def __init__(
        self,
        name: builtin.parts.APartName,
        mri: builtin.parts.AMri,
        initial_visibility: builtin.parts.AInitialVisibility = False,
    ) -> None:
        super().__init__(name, mri, initial_visibility)
        # If it was faulty at init, allow it to exist, and ignore reset commands
        # but don't let it be configured or run
        self.faulty: bool = False

    def setup(self, registrar):
        super().setup(registrar)
        # Hooks
        registrar.hook(PreConfigureHook, self.reload)
        registrar.hook(ConfigureHook, self.on_configure)
        registrar.hook(AbortHook, self.on_abort)

    def notify_dispatch_request(self, request: Request) -> None:
        if isinstance(request, Put) and request.path[1] == "design":
            # We have hooked self.reload to PreConfigure, and reload() will
            # set design attribute, so explicitly allow this without checking
            # it is in no_save (as it won't be in there)
            pass
        else:
            super().notify_dispatch_request(request)

    # Must match those passed in configure() Method, so need to be camelCase
    # noinspection PyPep8Naming
    @add_call_types
    def on_configure(
        self,
        context: AContext,
        generator: AGenerator,
        fileDir: AFileDir,
        fileTemplate: AFileTemplate = "%s.h5",
    ) -> UInfos:
        # Unlike DetectorChildPart we are always enabled when visible
        child = context.block_view(self.mri)
        # Make kwargs for the child
        kwargs = dict(
            generator=generator,
            fileDir=fileDir,
            # formatName is the unique part of the HDF filename, so use the part
            # name for this
            formatName=self.name,
            fileTemplate=fileTemplate,
        )
        child.configure(**kwargs)
        # Report back any datasets the child has to our parent
        assert hasattr(child, "datasets"), (
            f"Detector {self.mri} doesn't have a dataset table, did you add a "
            "scanning.parts.DatasetTablePart to it?"
        )
        datasets_table = child.datasets.value
        info_list = [DatasetProducedInfo(*row) for row in datasets_table.rows()]
        return info_list

    @add_call_types
    def on_init(self, context: AContext) -> None:
        try:
            super().on_init(context)
        except BadValueError:
            self.log.exception(
                f"Ethercat {self.name} was faulty at init and is not usable"
            )
            self.faulty = True

    @add_call_types
    def on_reset(self, context: AContext) -> None:
        if not self.faulty:
            child = context.block_view(self.mri)
            if child.abort.meta.writeable:
                child.abort()
            super().on_reset(context)

    @add_call_types
    def on_abort(self, context: AContext) -> None:
        child = context.block_view(self.mri)
        child.abort()
