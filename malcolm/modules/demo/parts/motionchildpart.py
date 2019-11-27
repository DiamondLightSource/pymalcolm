import time

from annotypes import Anno, add_call_types

from malcolm.core import PartRegistrar
from malcolm.modules import builtin, scanning

with Anno("If >0, raise an exception at the end of this step"):
    AExceptionStep = int


class MotionChildPart(builtin.parts.ChildPart):
    """Provides control of a `counter_block` within a `RunnableController`"""
    # Generator instance
    _generator = None  # type: scanning.hooks.AGenerator
    # Where to start
    _completed_steps = None  # type: int
    # How many steps to do
    _steps_to_do = None  # type: int
    # When to blow up
    _exception_step = None  # type: int
    # Which axes we should be moving
    _axes_to_move = None  # type: scanning.hooks.AAxesToMove

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(MotionChildPart, self).setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.PreConfigureHook, self.reload)
        registrar.hook((scanning.hooks.ConfigureHook,
                        scanning.hooks.PostRunArmedHook,
                        scanning.hooks.SeekHook), self.on_configure)
        registrar.hook(scanning.hooks.RunHook, self.on_run)
        # Tell the controller to expose some extra configure parameters
        registrar.report(scanning.hooks.ConfigureHook.create_info(
            self.on_configure))

    # For docs: Before configure
    # Allow CamelCase for arguments as they will be serialized by parent
    # noinspection PyPep8Naming
    @add_call_types
    def on_configure(self,
                     context,  # type: scanning.hooks.AContext
                     completed_steps,  # type: scanning.hooks.ACompletedSteps
                     steps_to_do,  # type: scanning.hooks.AStepsToDo
                     # The following were passed from user calling configure()
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
        child = context.block_view(self.mri)
        # Move to start (instantly)
        first_point = generator.get_point(completed_steps)
        for axis in self._axes_to_move:
            child["%sMove" % axis](first_point.lower[axis])

    @add_call_types
    def on_run(self, context):
        # type: (scanning.hooks.AContext) -> None
        # Start time so everything is relative
        point_time = time.time()
        child = context.block_view(self.mri)
        # This will hold the last move values of the motors
        move_values = {}
        # Get the asynchronous versions of the move methods
        async_move_methods = {}
        for axis in self._axes_to_move:
            async_move_methods[axis] = child[axis + "Move_async"]
            move_values[axis] = None
        for i in range(self._completed_steps,
                       self._completed_steps + self._steps_to_do):
            # Get the point we are meant to be scanning
            point = self._generator.get_point(i)
            # Update when the next point is due and how long motor moves take
            point_time += point.duration
            move_duration = point_time - time.time()
            # Move the children (instantly) to the beginning of the point, then
            # start them moving to the end of the point asynchronously, taking
            # duration seconds, populating a list of futures we can wait on
            fs = []
            for axis, move_async in async_move_methods.items():
                if move_values[axis] != point.lower[axis]:
                    fs.append(move_async(point.lower[axis]))
                move_values[axis] = point.upper[axis]
                fs.append(move_async(point.upper[axis], move_duration))
            context.wait_all_futures(fs)
            # Update the point as being complete
            self.registrar.report(scanning.infos.RunProgressInfo(i + 1))
            # If this is the exception step then blow up
            assert i + 1 != self._exception_step, \
                "Raising exception at step %s" % self._exception_step
