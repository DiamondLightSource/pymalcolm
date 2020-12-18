from typing import Optional

from annotypes import add_call_types

from malcolm.core import DEFAULT_TIMEOUT, AMri, APartName, Future, PartRegistrar
from malcolm.modules import ADCore, builtin, scanning
from malcolm.modules.builtin.parts import AInitialVisibility, AStateful, ChildPart


# We will set these attributes on the child block, so don't save them
@builtin.util.no_save(
    "enableCallbacks",
    "arrayCounter",
    "capture",
    "triggerMode",
    "averageSamples",
    "triggerCount",
)
class ReframePluginPart(ChildPart):
    """Part for controlling a 'reframe_plugin_block' in a Device"""

    def __init__(
        self,
        name: APartName,
        mri: AMri,
        initial_visibility: AInitialVisibility = False,
        stateful: AStateful = True,
    ) -> None:
        super().__init__(
            name, mri, initial_visibility=initial_visibility, stateful=stateful
        )
        # How long to wait between frame updates before error
        self.frame_timeout = 0.0
        # When arrayCounter gets to here we are done
        self.done_when_reaches = 0
        # CompletedSteps = arrayCounter + self.uniqueid_offset
        self.uniqueid_offset = 0
        # A future that completes when detector start calls back
        self.start_future: Optional[Future] = None

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(
            (
                scanning.hooks.ConfigureHook,
                scanning.hooks.PostRunArmedHook,
                scanning.hooks.SeekHook,
            ),
            self.on_configure,
        )
        registrar.hook(scanning.hooks.RunHook, self.on_run)
        registrar.hook(scanning.hooks.AbortHook, self.on_abort)

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def on_configure(
        self,
        context: scanning.hooks.AContext,
        completed_steps: scanning.hooks.ACompletedSteps,
        steps_to_do: scanning.hooks.AStepsToDo,
        generator: scanning.hooks.AGenerator,
    ) -> None:
        child = context.block_view(self.mri)

        # Calculate how long to wait before marking this scan as stalled
        self.frame_timeout = ADCore.util.FRAME_TIMEOUT
        if generator.duration > 0:
            self.frame_timeout += generator.duration
        else:
            # Double it to be safe
            self.frame_timeout += ADCore.util.FRAME_TIMEOUT

        if completed_steps == 0:
            # This is an initial configure, so reset arrayCounter to 0
            array_counter = 0
            self.done_when_reaches = steps_to_do
        else:
            # This is rewinding or setting up for another batch,
            # skip to a uniqueID that has not been produced yet
            array_counter = self.done_when_reaches
            self.done_when_reaches += steps_to_do
        self.uniqueid_offset = -completed_steps

        # Setup attributes
        fs = child.put_attribute_values_async(
            dict(
                arrayCounter=array_counter,
                enableCallbacks=True,
                triggerMode="Multiple",
                triggerCount=steps_to_do,
                averageSamples="Yes",
            )
        )
        context.wait_all_futures(fs)
        self.start_future = child.start_async()
        child.when_value_matches("acquireMode", "Armed", timeout=DEFAULT_TIMEOUT)

    @add_call_types
    def on_run(self, context: scanning.hooks.AContext) -> None:
        assert self.registrar, "No assigned registrar"
        self.wait_for_plugin(context, self.registrar, event_timeout=self.frame_timeout)

    def stop_plugin(self, context: scanning.hooks.AContext) -> None:
        child = context.block_view(self.mri)
        child.stop()
        child.when_value_matches("acquireMode", "Idle", timeout=DEFAULT_TIMEOUT)

    @add_call_types
    def on_abort(self, context: scanning.hooks.AContext,) -> None:
        self.stop_plugin(context)

    @add_call_types
    def on_reset(self, context: scanning.hooks.AContext) -> None:
        super().on_reset(context)
        self.stop_plugin(context)

    def update_completed_steps(self, value: int, registrar: PartRegistrar) -> None:
        completed_steps = value
        registrar.report(scanning.infos.RunProgressInfo(completed_steps))

    def wait_for_plugin(
        self,
        context: scanning.hooks.AContext,
        registrar: PartRegistrar,
        event_timeout: Optional[float] = None,
    ) -> None:
        child = context.block_view(self.mri)
        child.arrayCounterReadback.subscribe_value(
            self.update_completed_steps, registrar
        )
        # If no new frames produced in event_timeout seconds, consider scan dead
        context.wait_all_futures(self.start_future, event_timeout=event_timeout)
        # Now wait to make sure any update_completed_steps come in. Give
        # it 5 seconds to timeout just in case there are any stray frames that
        # haven't made it through yet
        child.when_value_matches(
            "triggerCountReadback",
            self.done_when_reaches + self.uniqueid_offset,
            timeout=DEFAULT_TIMEOUT,
        )
