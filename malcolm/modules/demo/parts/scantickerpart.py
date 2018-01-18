import time

from annotypes import Anno, add_call_types

from malcolm.core import Part, APartName, PartRegistrar
from malcolm.modules.builtin.parts import ChildPart, AMri
from malcolm.modules.scanning.hooks import ConfigureHook, PostRunArmedHook, \
    SeekHook, RunHook, ResumeHook, ACompletedSteps, AStepsToDo, AContext
from malcolm.modules.scanning.infos import ConfigureParamsInfo, RunProgressInfo
from malcolm.modules.scanning.util import ConfigureParams, AGenerator, \
    UAxesToMove


with Anno("If >0, raise an exception at the end of this step"):
    AExceptionStep = int


class ScanTickerParams(ConfigureParams):
    # This will be serialized, so maintain camelCase for axesToMove
    # noinspection PyPep8Naming
    def __init__(self, generator, axesToMove, exceptionStep=0):
        # type: (AGenerator, UAxesToMove, AExceptionStep) -> None
        super(ScanTickerParams, self).__init__(generator, axesToMove)
        self.exceptionStep = exceptionStep


with Anno("Configuration parameters passed in"):
    AScanTickerParams = ScanTickerParams


class ScanTickerPart(Part):
    """Provides control of a `counter_block` within a `RunnableController`"""

    def __init__(self, name, mri):
        # type: (APartName, AMri) -> None
        super(ScanTickerPart, self).__init__(name)
        self.mri = mri
        self.cp = ChildPart(name, mri)
        # Generator instance
        self.generator = None  # type: AGenerator
        # Where to start
        self.completed_steps = None  # type: int
        # How many steps to do
        self.steps_to_do = None  # type: int
        # When to blow up
        self.exception_step = None  # type: int
        # The registrar object we get at setup
        self.registrar = None  # type: PartRegistrar

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.registrar = registrar
        self.cp.setup(registrar)
        registrar.report(ConfigureParamsInfo(ScanTickerParams))

    def on_hook(self, hook):
        if isinstance(hook, (ConfigureHook, PostRunArmedHook, SeekHook)):
            hook.run(self.configure)
        elif isinstance(hook, (RunHook, ResumeHook)):
            hook.run(self.run)
        else:
            self.cp.on_hook(hook)

    @add_call_types
    def configure(self, completed_steps, steps_to_do, params):
        # type: (ACompletedSteps, AStepsToDo, AScanTickerParams) -> None
        # If we are being asked to move
        if self.name in params.axesToMove:
            # Just store the generator and place we need to start
            self.generator = params.generator
            self.completed_steps = completed_steps
            self.steps_to_do = steps_to_do
            self.exception_step = params.exceptionStep
        else:
            # Flag nothing to do
            self.generator = None

    @add_call_types
    def run(self, context):
        # type: (AContext) -> None
        # Start time so everything is relative
        point_time = time.time()
        if self.generator:
            child = context.block_view(self.params.mri)
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
                self.registrar.report(RunProgressInfo(i + 1))
                # If this is the exception step then blow up
                assert i + 1 != self.exception_step, \
                    "Raising exception at step %s" % self.exception_step
