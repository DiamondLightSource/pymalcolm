import time

from annotypes import Anno, add_call_types

from malcolm.core import APartName, PartRegistrar
from malcolm.modules import builtin, scanning

with Anno("If >0, raise an exception at the end of this step"):
    AExceptionStep = int


class ScanTickerPart(builtin.parts.ChildPart):
    """Provides control of a `counter_block` within a `RunnableController`"""

    def __init__(self, name, mri):
        # type: (APartName, builtin.parts.AMri) -> None
        super(ScanTickerPart, self).__init__(
            name, mri, initial_visibility=True, stateful=False)
        # Generator instance
        self.generator = None  # type: scanning.hooks.AGenerator
        # Where to start
        self.completed_steps = None  # type: int
        # How many steps to do
        self.steps_to_do = None  # type: int
        # When to blow up
        self.exception_step = None  # type: int
        # Hooks
        self.register_hooked((scanning.hooks.ConfigureHook,
                              scanning.hooks.PostRunArmedHook,
                              scanning.hooks.SeekHook), self.configure)
        self.register_hooked((scanning.hooks.RunHook,
                              scanning.hooks.ResumeHook), self.run)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(ScanTickerPart, self).setup(registrar)
        # Tell the controller to expose some extra configure parameters
        registrar.report(scanning.hooks.ConfigureHook.create_info(
            self.configure))

    # Allow CamelCase for arguments as they will be serialized by parent
    # noinspection PyPep8Naming
    @add_call_types
    def configure(self,
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  steps_to_do,  # type: scanning.hooks.AStepsToDo
                  # The following were passed from the user calling configure()
                  generator,  # type: scanning.hooks.AGenerator
                  axesToMove,  # type: scanning.hooks.AAxesToMove
                  exceptionStep=0,  # type: AExceptionStep
                  ):
        # type: (...) -> None
        # If we are being asked to move
        if self.name in axesToMove:
            # Just store the generator and place we need to start
            self.generator = generator
            self.completed_steps = completed_steps
            self.steps_to_do = steps_to_do
            self.exception_step = exceptionStep
        else:
            # Flag nothing to do
            self.generator = None

    @add_call_types
    def run(self, context):
        # type: (scanning.hooks.AContext) -> None
        if not self.generator:
            return
        # Start time so everything is relative
        point_time = time.time()
        child = context.block_view(self.mri)
        for i in range(self.completed_steps,
                       self.completed_steps + self.steps_to_do):
            self.log.debug("Starting point %s", i)
            # Get the point we are meant to be scanning
            point = self.generator.get_point(i)
            # Update the child counter_block to be the demand position
            position = point.positions[self.name]
            child.counter.put_value(position)
            # Wait until the next point is due
            point_time += point.duration
            wait_time = point_time - time.time()
            self.log.debug("%s Sleeping %s", self.name, wait_time)
            context.sleep(wait_time)
            # Update the point as being complete
            self.registrar.report(scanning.infos.RunProgressInfo(i + 1))
            # If this is the exception step then blow up
            assert i + 1 != self.exception_step, \
                "Raising exception at step %s" % self.exception_step
