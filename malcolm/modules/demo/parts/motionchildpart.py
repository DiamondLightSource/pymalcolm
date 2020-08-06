import time
from typing import Dict, List, Optional

from annotypes import Anno, add_call_types

from malcolm.core import Block, Future, PartRegistrar
from malcolm.modules import builtin, scanning

with Anno("If >0, raise an exception at the end of this step"):
    AExceptionStep = int


class MaybeMover:
    """Helper object that does async moves on an axis of a child Block only if
    the last move didn't move it to that position"""

    def __init__(self, child: Block, axis: str) -> None:
        self._last_move: Optional[float] = None
        self._move_async = child[axis + "Move_async"]

    def maybe_move_async(
        self, fs: List[Future], position: float, duration: float = None
    ) -> None:
        """If the last move was not to position, start an async move there,
        adding the Future to fs"""
        if self._last_move != position:
            self._last_move = position
            fs.append(self._move_async(position, duration))


class MotionChildPart(builtin.parts.ChildPart):
    """Provides control of a `counter_block` within a `RunnableController`"""

    # Generator instance
    _generator: scanning.hooks.AGenerator = None
    # Where to start
    _completed_steps: int = 0
    # How many steps to do
    _steps_to_do: int = 0
    # When to blow up
    _exception_step: int = 0
    # Which axes we should be moving
    _axes_to_move: Optional[scanning.hooks.AAxesToMove] = None
    # MaybeMover objects to help with async moves
    _movers: Dict[str, MaybeMover] = {}

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.PreConfigureHook, self.reload)
        registrar.hook(
            (
                scanning.hooks.ConfigureHook,
                scanning.hooks.PostRunArmedHook,
                scanning.hooks.SeekHook,
            ),
            self.on_configure,
        )
        registrar.hook(scanning.hooks.RunHook, self.on_run)
        # Tell the controller to expose some extra configure parameters
        registrar.report(scanning.hooks.ConfigureHook.create_info(self.on_configure))

    # For docs: Before configure
    # Allow CamelCase for arguments as they will be serialized by parent
    # noinspection PyPep8Naming
    @add_call_types
    def on_configure(
        self,
        context: scanning.hooks.AContext,
        completed_steps: scanning.hooks.ACompletedSteps,
        steps_to_do: scanning.hooks.AStepsToDo,
        # The following were passed from user calling configure()
        generator: scanning.hooks.AGenerator,
        axesToMove: scanning.hooks.AAxesToMove,
        exceptionStep: AExceptionStep = 0,
    ) -> None:
        child = context.block_view(self.mri)
        # Store the generator and place we need to start
        self._generator = generator
        self._completed_steps = completed_steps
        self._steps_to_do = steps_to_do
        self._exception_step = exceptionStep
        self._axes_to_move = axesToMove
        self._movers = {axis: MaybeMover(child, axis) for axis in axesToMove}
        # Move to start (instantly)
        first_point = generator.get_point(completed_steps)
        fs: List[Future] = []
        for axis, mover in self._movers.items():
            mover.maybe_move_async(fs, first_point.lower[axis])
        context.wait_all_futures(fs)

    @add_call_types
    def on_run(self, context: scanning.hooks.AContext) -> None:
        # Start time so everything is relative
        point_time = time.time()
        for i in range(
            self._completed_steps, self._completed_steps + self._steps_to_do
        ):
            # Get the point we are meant to be scanning
            point = self._generator.get_point(i)
            # Update when the next point is due and how long motor moves take
            point_time += point.duration
            move_duration = point_time - time.time()
            # Move the children (instantly) to the beginning of the point, then
            # start them moving to the end of the point, taking duration
            # seconds, populating a list of futures we can wait on
            fs: List[Future] = []
            for axis, mover in self._movers.items():
                mover.maybe_move_async(fs, point.lower[axis])
                mover.maybe_move_async(fs, point.upper[axis], move_duration)
            # Wait for the moves to complete
            context.wait_all_futures(fs)
            # Update the point as being complete
            assert self.registrar, "Part has no registrar"
            self.registrar.report(scanning.infos.RunProgressInfo(i + 1))
            # If this is the exception step then blow up
            assert i + 1 != self._exception_step, (
                "Raising exception at step %s" % self._exception_step
            )
