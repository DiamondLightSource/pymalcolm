import time

from annotypes import Anno, add_call_types

from malcolm.core import PartRegistrar
from malcolm.modules import builtin, scanning

with Anno("If >0, raise an exception at the end of this step"):
    AExceptionStep = int
AInitialVisibility = builtin.parts.AInitialVisibility


class MotionChildPart(builtin.parts.ChildPart):
    """Provides control of a `counter_block` within a `RunnableController`"""

    def __init__(self,
                 name,  # type: builtin.parts.APartName
                 mri,  # type: builtin.parts.AMri
                 initial_visibility=None,  # type: AInitialVisibility
                 ):
        # type: (...) -> None
        super(MotionChildPart, self).__init__(
            name, mri, initial_visibility, stateful=False)
        # Generator instance
        self._generator = None  # type: scanning.hooks.AGenerator
        # Where to start
        self._completed_steps = None  # type: int
        # How many steps to do
        self._steps_to_do = None  # type: int
        # When to blow up
        self._exception_step = None  # type: int
        # Which axes we should be moving
        self._axes_to_move = None  # type: scanning.hooks.AAxesToMove
        # Hooks
        self.register_hooked(scanning.hooks.PreConfigureHook, self.reload)
        self.register_hooked((scanning.hooks.ConfigureHook,
                              scanning.hooks.PostRunArmedHook,
                              scanning.hooks.SeekHook), self.configure)
        self.register_hooked((scanning.hooks.RunHook,
                              scanning.hooks.ResumeHook), self.run)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(MotionChildPart, self).setup(registrar)
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
        # Store the generator and place we need to start
        self._generator = generator
        self._completed_steps = completed_steps
        self._steps_to_do = steps_to_do
        self._exception_step = exceptionStep
        self._axes_to_move = axesToMove

    # Run scan
    @add_call_types
    def run(self, context):
        # type: (scanning.hooks.AContext) -> None
        # Start time so everything is relative
        point_time = time.time()
        child = context.block_view(self.mri)
        # Get the asynchronous versions of the move methods
        async_move_methods = {}
        for axis in self._axes_to_move:
            async_move_methods[axis] = child[axis + "Move_async"]
        for i in range(self._completed_steps,
                       self._completed_steps + self._steps_to_do):
            self.log.debug("Starting point %s", i)
            # Get the point we are meant to be scanning
            point = self._generator.get_point(i)
            # Start all the children moving at the same time, populating a list
            # of futures we can wait on
            fs = []
            for axis, move_async in async_move_methods.items():
                fs.append(move_async(point.positions[axis]))
            context.wait_all_futures(fs)
            # Wait until the next point is due
            point_time += point.duration
            wait_time = point_time - time.time()
            self.log.debug("%s Sleeping %s", self.name, wait_time)
            context.sleep(wait_time)
            # Update the point as being complete
            self.registrar.report(scanning.infos.RunProgressInfo(i + 1))
            # If this is the exception step then blow up
            assert i + 1 != self._exception_step, \
                "Raising exception at step %s" % self._exception_step
