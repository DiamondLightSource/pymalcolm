# Treat all division as float division even in python2
from __future__ import division

from annotypes import add_call_types, TYPE_CHECKING, Anno

from malcolm.core import DEFAULT_TIMEOUT
from malcolm.modules import builtin, scanning
from malcolm.modules.builtin.parts import ChildPart
from ..infos import MotorInfo

if TYPE_CHECKING:
    from typing import Dict


with Anno("Initial value for min time for any gaps between frames"):
    AMinTurnaround = float


class CSPart(ChildPart):
    def __init__(self,
                 name,  # type: builtin.parts.APartName
                 mri,  # type: builtin.parts.AMri
                 ):
        # type: (...) -> None
        super(CSPart, self).__init__(name, mri, initial_visibility=True)
        # Axis information stored from validate
        self.axis_mapping = None  # type: Dict[str, MotorInfo]
        # Hooks
        self.register_hooked((scanning.hooks.ConfigureHook,
                              scanning.hooks.PostRunArmedHook,
                              scanning.hooks.SeekHook), self.configure)
        self.register_hooked(scanning.hooks.AbortHook, self.abort)

    @add_call_types
    def reset(self, context):
        # type: (builtin.hooks.AContext) -> None
        super(CSPart, self).reset(context)
        self.abort(context)

    # Allow CamelCase as arguments will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  part_info,  # type: scanning.hooks.APartInfo
                  generator,  # type: scanning.hooks.AGenerator
                  axesToMove,  # type: scanning.hooks.AAxesToMove
                  ):
        # type: (...) -> None
        child = context.block_view(self.mri)
        cs_port, self.axis_mapping = MotorInfo.cs_axis_mapping(
            part_info, axesToMove)
        # Check units for everything in the axis mapping
        for axis_name, motor_info in sorted(self.axis_mapping.items()):
            assert motor_info.units == generator.units[axis_name], \
                "%s: Expected scan units of %r, got %r" % (
                    axis_name, motor_info.units, generator.units[axis_name])
        # See if we are the CS that should do the moving
        if cs_port != child.port.value:
            return
        # Set all the axes to move to the start positions
        child.deferMoves.put_value(1)
        child.csMoveTime.put_value(0)
        first_point = generator.get_point(completed_steps)
        start_positions = {}
        move_to_start_time = 0.0
        for axis_name, velocity in self.point_velocities(first_point).items():
            motor_info = self.axis_mapping[axis_name]  # type: MotorInfo
            acceleration_distance = motor_info.ramp_distance(0, velocity)
            start_pos = first_point.lower[axis_name] - acceleration_distance
            start_positions["demand" + motor_info.cs_axis] = start_pos
            # Time profile that the move is likely to take
            # NOTE: this is only accurate if pmac max velocity in linear motion
            # prog is set to same speed as motor record VMAX
            times, _ = motor_info.make_velocity_profile(
                0, 0, motor_info.current_position - start_pos, 0)
            move_to_start_time = max(times[-1], move_to_start_time)
        # Start them off moving, can't wait forever
        fs = child.put_attribute_values_async(
            {attr: value for attr, value in start_positions.items()})
        # Wait for the demand to have been received by the PV
        for attr, value in start_positions.items():
            child.when_value_matches(attr, value, timeout=1.0)
        # Start the move
        child.deferMoves.put_value(0)
        # Wait for the moves to complete
        context.wait_all_futures(
            fs, timeout=move_to_start_time + DEFAULT_TIMEOUT)

    @add_call_types
    def abort(self, context):
        # type: (scanning.hooks.AContext) -> None
        child = context.block_view(self.mri)
        child.abort()

    def point_velocities(self, point):
        """Find the velocities of each axis over the current point"""
        velocities = {}
        for axis_name, motor_info in self.axis_mapping.items():
            full_distance = point.upper[axis_name] - point.lower[axis_name]
            velocities[axis_name] = full_distance / point.duration
        return velocities

