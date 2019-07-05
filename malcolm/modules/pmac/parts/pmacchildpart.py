# Treat all division as float division even in python2
from __future__ import division

import re

import numpy as np
from annotypes import add_call_types, TYPE_CHECKING
from enum import Enum
from scanpointgenerator import CompoundGenerator

from malcolm.core import Future, Block, PartRegistrar, Put, Request
from malcolm.modules import builtin, scanning
from malcolm.modules.pmac.util import get_motion_trigger
from ..infos import MotorInfo
from ..util import cs_axis_mapping, points_joined, point_velocities, MIN_TIME, \
    profile_between_points, cs_port_with_motors_in, get_motion_axes

if TYPE_CHECKING:
    from typing import Dict, List

# Number of seconds that a trajectory tick is
TICK_S = 0.000001

# Interval for interpolating velocity curves
INTERPOLATE_INTERVAL = 0.02

# Longest move time we can request
MAX_MOVE_TIME = 4.0

# velocity modes
PREV_TO_NEXT = 0
PREV_TO_CURRENT = 1
CURRENT_TO_NEXT = 2
ZERO_VELOCITY = 3

# user programs
NO_PROGRAM = 0    # Do nothing
LIVE_PROGRAM = 1  # GPIO123 = 1, 0, 0
DEAD_PROGRAM = 2  # GPIO123 = 0, 1, 0
MID_PROGRAM = 4   # GPIO123 = 0, 0, 1
ZERO_PROGRAM = 8  # GPIO123 = 0, 0, 0


class PointType(Enum):
    START_OF_ROW = 0  # Lower bound of first point of row
    MID_POINT = 1  # Position of any point
    POINT_JOIN = 2  # Boundary of two joined points
    END_OF_ROW = 3  # Upper boundary of last point of row
    TURNAROUND = 4  # Between rows


# How many profile points to write each time
PROFILE_POINTS = 10000

# 80 char line lengths...
AIV = builtin.parts.AInitialVisibility

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri


class PmacChildPart(builtin.parts.ChildPart):
    def __init__(self,
                 name,  # type: APartName
                 mri,  # type: AMri
                 initial_visibility=None  # type: AIV
                 ):
        # type: (...) -> None
        super(PmacChildPart, self).__init__(name, mri, initial_visibility)
        # Axis information stored from validate
        self.axis_mapping = None  # type: Dict[str, MotorInfo]
        # Lookup of the completed_step value for each point
        self.completed_steps_lookup = []  # type: List[int]
        # The minimum turnaround time for non-joined points
        self.min_turnaround = 0
        # If we are currently loading then block loading more points
        self.loading = False
        # Where we have generated into profile
        self.end_index = 0
        # Where we should stop loading points
        self.steps_up_to = 0
        # What sort of triggers to output
        self.output_triggers = None
        # Profile points that haven't been sent yet
        # {timeArray/velocityMode/userPrograms/a/b/c/u/v/w/x/y/z: [elements]}
        self.profile = {}
        # Stored generator for positions
        self.generator = None  # type: CompoundGenerator

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(PmacChildPart, self).setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ValidateHook, self.validate)
        registrar.hook(scanning.hooks.PreConfigureHook, self.reload)
        registrar.hook((scanning.hooks.ConfigureHook,
                        scanning.hooks.PostRunArmedHook,
                        scanning.hooks.SeekHook), self.configure)
        registrar.hook((scanning.hooks.RunHook,
                        scanning.hooks.ResumeHook), self.run)
        registrar.hook((scanning.hooks.AbortHook,
                        scanning.hooks.PauseHook), self.abort)

    def notify_dispatch_request(self, request):
        # type: (Request) -> None
        if isinstance(request, Put) and request.path[1] == "design":
            # We have hooked self.reload to PreConfigure, and reload() will
            # set design attribute, so explicitly allow this without checking
            # it is in no_save (as it won't be in there)
            pass
        else:
            super(PmacChildPart, self).notify_dispatch_request(request)

    @add_call_types
    def reset(self, context):
        # type: (builtin.hooks.AContext) -> None
        super(PmacChildPart, self).reset(context)
        self.abort(context)

    # Allow CamelCase as arguments will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def validate(self,
                 context,  # type: scanning.hooks.AContext
                 generator,  # type: scanning.hooks.AGenerator
                 axesToMove,  # type: scanning.hooks.AAxesToMove
                 part_info,  # type: scanning.hooks.APartInfo
                 ):
        # type: (...) -> scanning.hooks.UParameterTweakInfos
        child = context.block_view(self.mri)
        # Check that we can move all the requested axes
        available = set(child.layout.value.name)
        motion_axes = get_motion_axes(generator, axesToMove)
        assert available.issuperset(motion_axes), \
            "Some of the requested axes %s are not on the motor list %s" % (
                list(axesToMove), sorted(available))
        # If GPIO not demanded for every point we don't need to align to the
        # servo cycle
        trigger = get_motion_trigger(part_info)
        if trigger != scanning.infos.MotionTrigger.EVERY_POINT:
            return
        # Find the duration
        assert generator.duration > 0, \
            "Can only do fixed duration at the moment"
        servo_freq = child.servoFrequency()
        # convert half an exposure to multiple of servo ticks, rounding down
        ticks = np.floor(servo_freq * 0.5 * generator.duration)
        if not np.isclose(servo_freq, 3200):
            # + 0.002 for some observed jitter in the servo frequency if I10
            # isn't a whole number of 1/4 us move timer ticks
            # (any frequency apart from 3.2 kHz)
            ticks += 0.002
        # convert to integer number of microseconds, rounding up
        micros = np.ceil(ticks / servo_freq * 1e6)
        # back to duration
        duration = 2 * float(micros) / 1e6
        if duration != generator.duration:
            serialized = generator.to_dict()
            new_generator = CompoundGenerator.from_dict(serialized)
            new_generator.duration = duration
            return scanning.infos.ParameterTweakInfo("generator", new_generator)

    def move_to_start(self, child, cs_port, completed_steps):
        # type: (Block, str, int) -> Future
        # Work out what method to call
        match = re.search("\d+$", cs_port)
        assert match, "Cannot extract CS number from CS port '%s'" % cs_port
        move_async = child["moveCS%s_async" % match.group()]
        # Set all the axes to move to the start positions
        first_point = self.generator.get_point(completed_steps)
        args = {}
        move_to_start_time = 0.0
        for axis_name, velocity in point_velocities(
                self.axis_mapping, first_point).items():
            motor_info = self.axis_mapping[axis_name]  # type: MotorInfo
            acceleration_distance = motor_info.ramp_distance(0, velocity)
            start_pos = first_point.lower[axis_name] - acceleration_distance
            args[motor_info.cs_axis.lower()] = start_pos
            # Time profile that the move is likely to take
            # NOTE: this is only accurate if pmac max velocity in linear motion
            # prog is set to same speed as motor record VMAX
            times, _ = motor_info.make_velocity_profile(
                0, 0, motor_info.current_position - start_pos, 0)
            move_to_start_time = max(times[-1], move_to_start_time)
        # Call the method with the values
        fs = move_async(moveTime=move_to_start_time, **args)
        return fs

    # Allow CamelCase as arguments will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  steps_to_do,  # type: scanning.hooks.AStepsToDo
                  part_info,  # type: scanning.hooks.APartInfo
                  generator,  # type: scanning.hooks.AGenerator
                  axesToMove,  # type: scanning.hooks.AAxesToMove
                  ):
        # type: (...) -> None
        context.unsubscribe_all()
        child = context.block_view(self.mri)

        # Store what sort of triggers we need to output
        self.output_triggers = get_motion_trigger(part_info)

        # Check if we should be taking part in the scan
        motion_axes = get_motion_axes(generator, axesToMove)
        need_gpio = self.output_triggers != scanning.infos.MotionTrigger.NONE
        if motion_axes or need_gpio:
            # Taking part, so store generator
            self.generator = generator
        else:
            # Flag as not taking part
            self.generator = None
            return

        # See if there is a minimum turnaround
        infos = scanning.infos.MinTurnaroundInfo.filter_values(part_info)
        if infos:
            assert len(infos) == 1, \
                "Expected 0 or 1 MinTurnaroundInfos, got %d" % len(infos)
            self.min_turnaround = max(MIN_TIME, infos[0].gap)
        else:
            self.min_turnaround = MIN_TIME

        # Work out the cs_port we should be using
        layout_table = child.layout.value
        if motion_axes:
            self.axis_mapping = cs_axis_mapping(
                context, layout_table, motion_axes)
            # Check units for everything in the axis mapping
            # TODO: reinstate this when GDA does it properly
            # for axis_name, motor_info in sorted(self.axis_mapping.items()):
            #     assert motor_info.units == generator.units[axis_name], \
            #         "%s: Expected scan units of %r, got %r" % (
            #         axis_name, motor_info.units, generator.units[axis_name])
            # Guaranteed to have an entry in axis_mapping otherwise
            # cs_axis_mapping would fail, so pick its cs_port
            cs_port = list(self.axis_mapping.values())[0].cs_port
        else:
            # No axes to move, but if told to output triggers we still need to
            # do something
            self.axis_mapping = {}
            # Pick the first cs we find that has an axis assigned
            cs_port = cs_port_with_motors_in(context, layout_table)

        # Reset GPIOs
        # TODO: we might need to put this in pause if the PandA logic doesn't
        # copy with a trigger staying high
        child.writeProfile(csPort=cs_port, timeArray=[MIN_TIME],
                           userPrograms=[ZERO_PROGRAM])
        child.executeProfile()
        if motion_axes:
            # Start off the move to the start
            fs = self.move_to_start(child, cs_port, completed_steps)
        else:
            fs = []
        # Set how far we should be going and the completed steps lookup
        self.steps_up_to = completed_steps + steps_to_do
        self.completed_steps_lookup = []
        # Reset the profiles that still need to be sent
        self.profile = dict(
            timeArray=[],
            velocityMode=[],
            userPrograms=[])
        for info in self.axis_mapping.values():
            self.profile[info.cs_axis.lower()] = []
        self.calculate_generator_profile(completed_steps, do_run_up=True)
        self.write_profile_points(child, cs_port)
        # Wait for the motors to have got to the start
        context.wait_all_futures(fs)

    @add_call_types
    def run(self, context):
        # type: (scanning.hooks.AContext) -> None
        if self.generator:
            self.loading = False
            child = context.block_view(self.mri)
            # Wait for the trajectory to run and complete
            child.pointsScanned.subscribe_value(self.update_step, child)
            # TODO: we should return at the end of the last point for PostRun
            child.executeProfile()

    @add_call_types
    def abort(self, context):
        # type: (scanning.hooks.AContext) -> None
        if self.generator:
            child = context.block_view(self.mri)
            # TODO: if we abort during move to start, what happens?
            child.abortProfile()

    def update_step(self, scanned, child):
        # scanned is an index into the completed_steps_lookup, so a
        # "how far through the pmac trajectory" rather than a generator
        # scan step
        if scanned > 0:
            completed_steps = self.completed_steps_lookup[scanned - 1]
            self.registrar.report(scanning.infos.RunProgressInfo(
                completed_steps))
            # Keep PROFILE_POINTS trajectory points in front
            if not self.loading and self.end_index < self.steps_up_to and \
                    len(self.completed_steps_lookup) - scanned < PROFILE_POINTS:
                self.loading = True
                self.calculate_generator_profile(self.end_index)
                self.write_profile_points(child)
                self.loading = False

            # If we got to the end, there might be some leftover points that
            # need to be appended to finish
            if not self.loading and self.end_index == self.steps_up_to and \
                    self.profile["timeArray"]:
                self.loading = True
                self.calculate_generator_profile(self.end_index)
                self.write_profile_points(child)
                assert not self.profile["timeArray"], \
                    "Why do we still have points? %s" % self.profile
                self.loading = False

    def write_profile_points(self, child, cs_port=None):
        """Build profile using given data

        Args:
            child (Block): Child block for running
            cs_port (str): CS Port if this is a build rather than append
        """
        # These are the things we will send
        args = {}
        if cs_port is not None:
            args["csPort"] = cs_port

        for k, v in self.profile.items():
            # store the remnant back in the array
            self.profile[k] = v[PROFILE_POINTS:]
            v = v[:PROFILE_POINTS]
            if k == "timeArray":
                overflow = 0.0
                time_array_ticks = []
                for t in v:
                    ticks = t / TICK_S
                    overflow += (ticks % 1)
                    ticks = int(ticks)
                    if overflow > 0.5:
                        overflow -= 1
                        ticks += 1
                    time_array_ticks.append(ticks)
                # TODO: overflow discarded overy 10000 points, is it a problem?
                v = np.array(time_array_ticks, np.int32)
            elif k in ("velocityMode", "userPrograms"):
                v = np.array(v, np.int32)
            else:
                v = np.array(v, np.float64)
            args[k] = v

        child.writeProfile(**args)

    def get_user_program(self, point_type):
        # type: (PointType) -> int
        if self.output_triggers == scanning.infos.MotionTrigger.NONE:
            # Always produce no program
            return NO_PROGRAM
        elif self.output_triggers == scanning.infos.MotionTrigger.ROW_GATE:
            if point_type == PointType.START_OF_ROW:
                # Produce a gate for the whole row
                return LIVE_PROGRAM
            elif point_type == PointType.END_OF_ROW:
                # Falling edge of row gate
                return ZERO_PROGRAM
            else:
                # Otherwise don't change anything
                return NO_PROGRAM
        else:
            if point_type in (PointType.START_OF_ROW, PointType.POINT_JOIN):
                return LIVE_PROGRAM
            elif point_type == PointType.END_OF_ROW:
                return DEAD_PROGRAM
            elif point_type == PointType.MID_POINT:
                return MID_PROGRAM
            else:
                return ZERO_PROGRAM

    def calculate_profile_from_velocities(self, time_arrays, velocity_arrays,
                                          current_positions, completed_steps):
        trajectory = {}

        # Interpolate the velocity arrays at about INTERPOLATE_INTERVAL
        move_time = max(t[-1] for t in time_arrays.values())
        # Make sure there are at least 2 of them
        num_intervals = max(int(np.floor(move_time / INTERPOLATE_INTERVAL)), 2)
        interval = move_time / num_intervals
        self.profile["timeArray"] += [interval] * num_intervals
        self.profile["velocityMode"] += \
            [PREV_TO_NEXT] * (num_intervals - 1) + [CURRENT_TO_NEXT]
        user_program = self.get_user_program(PointType.TURNAROUND)
        self.profile["userPrograms"] += [user_program] * num_intervals
        self.completed_steps_lookup += [completed_steps] * num_intervals

        # Do this for each velocity array
        for axis_name, motor_info in self.axis_mapping.items():
            trajectory[axis_name] = []
            ts = time_arrays[axis_name]
            vs = velocity_arrays[axis_name]
            position = current_positions[axis_name]
            # at this point we have time/velocity arrays with 5-7 values and
            # want to create a matching move profile with 'num_intervals'
            # steps, each separated by 'interval' seconds. Walk through the
            # profile steps aiming for the next time/velocity. Pop a
            # time/velocity pair off of the lists as the total elapsed profile
            # time exceeds the next point in the time/velocity pair.
            #
            # As we get to each profile point we set its velocity to be
            # between the velocities of the two surrounding velocity points.
            # The fraction of the time interval between the previous and next
            # velocity points is used to determine what fraction of the change
            # in velocity is applied at this profile point.
            for i in range(num_intervals):
                time = interval * (i + 1)
                # If we have exceeded the current segment, pop it and add it's
                # position in time
                # use while on this check in case multiple segments exceeded
                while time > ts[1] and not np.isclose(time, ts[1]):
                    position += motor_info.ramp_distance(
                        vs[0], vs[1], ts[1] - ts[0])
                    vs = vs[1:]
                    ts = ts[1:]
                assert len(ts) > 1, \
                    "Bad %s time %s velocity %s" % (time, ts, vs)
                fraction = (time - ts[0]) / (ts[1] - ts[0])
                velocity = fraction * (vs[1] - vs[0]) + vs[0]
                part_position = motor_info.ramp_distance(
                    vs[0], velocity, time - ts[0])
                self.profile[motor_info.cs_axis.lower()].append(
                    position + part_position)

    def add_profile_point(self, time_point, velocity_mode, user_program,
                          completed_step, axis_points):

        # Add padding if the move time exceeds the max pmac move time
        if time_point > MAX_MOVE_TIME:
            assert self.profile["timeArray"], \
                "Can't stretch the first point of a profile"
            nsplit = int(time_point / MAX_MOVE_TIME + 1)
            for _ in range(nsplit):
                self.profile["timeArray"].append(time_point / nsplit)
            for _ in range(nsplit - 1):
                self.profile["velocityMode"].append(PREV_TO_NEXT)
                self.profile["userPrograms"].append(NO_PROGRAM)
            for k, v in axis_points.items():
                cs_axis = self.axis_mapping[k].cs_axis.lower()
                last_point = self.profile[cs_axis][-1]
                per_section = float(v - last_point) / nsplit
                for i in range(1, nsplit):
                    self.profile[cs_axis].append(
                        last_point + i * per_section)
            last_completed_step = self.completed_steps_lookup[-1]
            for _ in range(nsplit - 1):
                self.completed_steps_lookup.append(last_completed_step)
        else:
            # Add point
            self.profile["timeArray"].append(time_point)

        # Set the requested point
        self.profile["velocityMode"].append(velocity_mode)
        self.profile["userPrograms"].append(user_program)
        self.completed_steps_lookup.append(completed_step)
        for k, v in axis_points.items():
            cs_axis = self.axis_mapping[k].cs_axis.lower()
            self.profile[cs_axis].append(v)

    def calculate_generator_profile(self, start_index, do_run_up=False):
        # If we are doing the first build, do_run_up will be passed to flag
        # that we need a run up, else just continue from the previous point
        if do_run_up:
            point = self.generator.get_point(start_index)

            # Calculate how long to leave for the run-up (at least MIN_TIME)
            run_up_time = MIN_TIME
            axis_points = {}
            for axis_name, velocity in point_velocities(
                    self.axis_mapping, point).items():
                axis_points[axis_name] = point.lower[axis_name]
                motor_info = self.axis_mapping[axis_name]
                run_up_time = max(run_up_time,
                                  motor_info.acceleration_time(0, velocity))

            # Add lower bound
            user_program = self.get_user_program(PointType.START_OF_ROW)
            self.add_profile_point(
                run_up_time, CURRENT_TO_NEXT, user_program, start_index,
                axis_points)

        for i in range(start_index, self.steps_up_to):
            point = self.generator.get_point(i)

            # Add position
            user_program = self.get_user_program(PointType.MID_POINT)
            self.add_profile_point(
                point.duration / 2.0, PREV_TO_NEXT, user_program, i,
                {name: point.positions[name] for name in self.axis_mapping})

            # If there will be more frames, insert next live frame
            if i + 1 < self.steps_up_to:
                # Check if we need to insert the lower bound of next_point
                next_point = self.generator.get_point(i + 1)
                points_are_joined = points_joined(
                    self.axis_mapping, point, next_point)

                if points_are_joined:
                    user_program = self.get_user_program(PointType.POINT_JOIN)
                    velocity_point = PREV_TO_NEXT
                else:
                    user_program = self.get_user_program(PointType.END_OF_ROW)
                    velocity_point = PREV_TO_CURRENT
                self.add_profile_point(
                    point.duration / 2.0, velocity_point, user_program, i + 1,
                    {name: point.upper[name] for name in self.axis_mapping})

                if not points_are_joined:
                    self.insert_gap(point, next_point, i + 1)
            else:
                # No more frames, dead frame to finish
                user_program = self.get_user_program(PointType.END_OF_ROW)
                self.add_profile_point(
                    point.duration / 2.0, PREV_TO_CURRENT, user_program, i + 1,
                    {name: point.upper[name] for name in self.axis_mapping})

            # Check if we have exceeded the points number and need to write
            # Strictly less than so we always add one more point to the time
            # array so we can always stretch points in a subsequent add with
            # the values already in the profiles
            if len(self.profile["timeArray"]) > PROFILE_POINTS:
                self.end_index = i + 1
                return

        # Add the last tail off point
        point = self.generator.get_point(self.steps_up_to - 1)

        # Calculate how long to leave for the tail-off (at least MIN_TIME)
        axis_points = {}
        tail_off_time = MIN_TIME
        for axis_name, velocity in point_velocities(
                self.axis_mapping, point, entry=False).items():
            motor_info = self.axis_mapping[axis_name]
            tail_off_time = max(tail_off_time,
                                motor_info.acceleration_time(0, velocity))
            tail_off = motor_info.ramp_distance(velocity, 0)
            axis_points[axis_name] = point.upper[axis_name] + tail_off

        # Do the last move
        user_program = self.get_user_program(PointType.TURNAROUND)
        self.add_profile_point(tail_off_time, ZERO_VELOCITY, user_program,
                               self.steps_up_to, axis_points)
        self.end_index = self.steps_up_to

    def insert_gap(self, point, next_point, completed_steps):
        # Work out the velocity profiles of how to move to the start
        time_arrays, velocity_arrays = profile_between_points(
            self.axis_mapping, point, next_point, self.min_turnaround)

        start_positions = {}
        for axis_name in self.axis_mapping:
            start_positions[axis_name] = point.upper[axis_name]

        # Work out the Position trajectories from these profiles
        self.calculate_profile_from_velocities(
            time_arrays, velocity_arrays, start_positions, completed_steps)

        # Change the last point to be a live frame
        self.profile["velocityMode"][-1] = CURRENT_TO_NEXT
        user_program = self.get_user_program(PointType.START_OF_ROW)
        self.profile["userPrograms"][-1] = user_program
