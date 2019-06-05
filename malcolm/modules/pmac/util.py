# Treat all division as float division even in python2
from __future__ import division

from collections import Counter

from annotypes import TYPE_CHECKING, Array
from scanpointgenerator import Point
import numpy as np

from malcolm.core import Context
from malcolm.modules import builtin
from .infos import MotorInfo

if TYPE_CHECKING:
    from typing import Tuple, Dict, Set, List
    Profiles = Dict[str, List[float]]


# All possible PMAC CS axis assignment
CS_AXIS_NAMES = list("ABCUVWXYZ")

# Minimum move time for any move
MIN_TIME = 0.002


def cs_port_with_motors_in(context,  # type: Context
                           layout_table,  # type: builtin.util.LayoutTable
                           ):
    # type: (...) -> str
    for mri in layout_table.mri:
        child = context.block_view(mri)
        cs = child.cs.value
        if cs:
            cs_port, cs_axis = child.cs.value.split(",", 1)
            if cs_axis in CS_AXIS_NAMES:
                return cs_port
    raise ValueError("Can't find a cs port to use in %s" % layout_table.name)


def cs_axis_mapping(context,  # type: Context
                    layout_table,  # type: builtin.util.LayoutTable
                    axes_to_move  # type: Array[str]
                    ):
    # type: (...) -> Dict[str, MotorInfo]
    """Given the layout table of a PMAC, create a MotorInfo for every axis in
    axes_to_move. Check that they are all in the same CS"""
    cs_ports = set()  # type: Set[str]
    axis_mapping = {}  # type: Dict[str, MotorInfo]
    for name, mri in zip(layout_table.name, layout_table.mri):
        if name in axes_to_move:
            child = context.block_view(mri)
            max_velocity = child.maxVelocity.value
            acceleration = float(max_velocity) / child.accelerationTime.value
            cs = child.cs.value
            if cs:
                cs_port, cs_axis = child.cs.value.split(",", 1)
            else:
                cs_port, cs_axis = "", ""
            assert cs_axis in CS_AXIS_NAMES, \
                "Can only scan 1-1 mappings, %r is %r" % (
                    name, cs_axis)
            cs_ports.add(cs_port)
            axis_mapping[name] = MotorInfo(
                cs_axis=cs_axis,
                cs_port=cs_port,
                acceleration=acceleration,
                resolution=child.resolution.value,
                offset=child.offset.value,
                max_velocity=max_velocity,
                current_position=child.readback.value,
                scannable=name,
                velocity_settle=child.velocitySettle.value,
                units=child.units.value
            )
    missing = list(set(axes_to_move) - set(axis_mapping))
    assert not missing, \
        "Some scannables %s are not in the CS mapping %s" % (
            missing, axis_mapping)
    assert len(cs_ports) == 1, \
        "Requested axes %s are in multiple CS numbers %s" % (
            axes_to_move, list(cs_ports))
    cs_axis_counts = Counter([x.cs_axis for x in axis_mapping.values()])
    # Any cs_axis defs that are used for more that one raw motor
    overlap = [k for k, v in cs_axis_counts.items() if v > 1]
    assert not overlap, \
        "CS axis defs %s have more that one raw motor attached" % overlap
    return axis_mapping


def points_joined(axis_mapping, point, next_point):
    # type: (Dict[str, MotorInfo], Point, Point) -> bool
    """Check for axes that need to move within the space between points"""
    for axis_name in axis_mapping:
        if point.upper[axis_name] != next_point.lower[axis_name]:
            return False
    return True


def point_velocities(axis_mapping, point, entry=True):
    # type: (Dict[str, MotorInfo], Point, bool) -> Dict[str, float]
    """Find the velocities of each axis over the entry/exit of current point"""
    velocities = {}
    for axis_name, motor_info in axis_mapping.items():
        #            x
        #        x       x
        #    x               x
        #    vl  vlp vp  vpu vu
        # Given distances from point,lower, position, upper, calculate
        # velocity at entry (vl) or exit (vu) of point by extrapolation
        dp = point.upper[axis_name] - point.lower[axis_name]
        vp = dp / point.duration
        if entry:
            # Halfway point is vlp, so calculate dlp
            dhalf = point.positions[axis_name] - point.lower[axis_name]
        else:
            # Halfway point is vpu, so calculate dpu
            dhalf = point.upper[axis_name] - point.positions[axis_name]
        # Extrapolate to get our entry or exit velocity
        # (vl + vp) / 2 = vlp
        # so vl = 2 * vlp - vp
        # where vlp = dlp / (t/2)
        velocity = 4 * dhalf / point.duration - vp
        assert abs(velocity) < motor_info.max_velocity, \
            "Velocity %s invalid for %r with max_velocity %s" % (
                velocity, axis_name, motor_info.max_velocity)
        velocities[axis_name] = velocity
    return velocities


def profile_between_points(axis_mapping, point, next_point, min_time=MIN_TIME):
    # type: (Dict[str, MotorInfo], Point, Point) -> Tuple[Profiles, Profiles]
    """Make consistent time and velocity arrays for each axis

    Try to create velocity profiles for all axes that all arrive at
    'distance' in the same time period. The profiles will contain the
    following points:-

    - start point at 0 secs with velocity v1     start decelerating
    - zero velocity point                        reached 0 speed
    - [optional] zero velocity end point         start accelerating
    - max velocity point                         achieved max speed
    - [optional] max velocity end point          start decelerating
    - zero velocity point                        reached 0 speed
    - end point with velocity v2                 reached target speed

    If the profile has to be stretched to achieve min_time then the
    first zero velocity point is stretched to zero velocity end point.

    If the axis never reaches maximum velocity then there is no max_velocity
    end point. The acceleration just switches direction at max velocity
    point. There are therefore between 5 and 7 points in a profile.

    After generating all the profiles this function checks to ensure they
    have all achieved min_time. If not min_time is reset to the slowest
    profile and all profiles are recalculated.

    Note that for each profile the area under the velocity/time plot
    must equal 'distance'. motor_info.make_velocity_profile uses
    _make_hat to do this.
    """
    start_velocities = point_velocities(axis_mapping, point)
    end_velocities = point_velocities(axis_mapping, next_point, entry=False)

    time_arrays = {}
    velocity_arrays = {}
    iterations = 5
    while iterations > 0:
        for axis_name, motor_info in axis_mapping.items():
            distance = next_point.lower[axis_name] - point.upper[axis_name]
            time_array, velocity_array = \
                motor_info.make_velocity_profile(
                    start_velocities[axis_name], end_velocities[axis_name],
                    distance, min_time)
            assert time_array[-1] >= min_time or np.isclose(
                time_array[-1], min_time), \
                "Time %s velocity %s for %s takes less time than %s" % (
                    time_array, velocity_array, axis_name, min_time)
            # Absolute time values that we are at that velocity
            time_arrays[axis_name] = time_array
            velocity_arrays[axis_name] = velocity_array
        new_min_time = max(t[-1] for t in time_arrays.values())
        if np.isclose(new_min_time, min_time):
            # We've got our consistent set
            return time_arrays, velocity_arrays
        else:
            min_time = new_min_time
            iterations -= 1
    raise ValueError("Can't get a consistent time in 5 iterations")
