import re
from enum import Enum
from typing import Dict, List, Optional, Union

import numpy as np
from annotypes import add_call_types
from scanpointgenerator import CompoundGenerator

from malcolm.core import Block, Future, PartRegistrar, Put, Request
from malcolm.modules import builtin, scanning
from malcolm.modules.pmac.util import get_motion_trigger
from malcolm.modules.scanning.infos import MinTurnaroundInfo, MotionTrigger

from ..infos import MotorInfo
from ..util import (
    MIN_INTERVAL,
    MIN_TIME,
    all_points_joined,
    all_points_same_velocities,
    cs_axis_mapping,
    cs_port_with_motors_in,
    get_motion_axes,
    point_velocities,
    profile_between_points,
)

# Number of seconds that a trajectory tick is
TICK_S = 0.000001

# Longest move time we can request
MAX_MOVE_TIME = 4.0


# velocity modes
class VelocityModes:
    AVERAGE_PREV_TO_NEXT = 0
    REAL_PREV_TO_CURRENT = 1
    AVERAGE_PREV_TO_CURRENT = 2
    ZERO_VELOCITY = 3


# user programs
class UserPrograms:
    NO_PROGRAM = 0  # Do nothing
    LIVE_PROGRAM = 1  # GPIO123 = 1, 0, 0
    DEAD_PROGRAM = 2  # GPIO123 = 0, 1, 0
    MID_PROGRAM = 4  # GPIO123 = 0, 0, 1
    ZERO_PROGRAM = 8  # GPIO123 = 0, 0, 0


class PointType(Enum):
    START_OF_ROW = 0  # Lower bound of first point of row
    MID_POINT = 1  # Position of any point
    POINT_JOIN = 2  # Boundary of two joined points
    END_OF_ROW = 3  # Upper boundary of last point of row
    TURNAROUND = 4  # Between rows


# How many profile points to write each time
PROFILE_POINTS = 2000
# How many points to extract from a scanpointgenerator each time
BATCH_POINTS = 20000

# 80 char line lengths...
AIV = builtin.parts.AInitialVisibility

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri


class PmacChildPart(builtin.parts.ChildPart):
    def __init__(
        self, name: APartName, mri: AMri, initial_visibility: AIV = False
    ) -> None:
        super().__init__(name, mri, initial_visibility)
        # Axis information stored from validate
        self.axis_mapping: Dict[str, MotorInfo] = {}
        # Lookup of the completed_step value for each point
        self.completed_steps_lookup: List[int] = []
        # The minimum turnaround time for non-joined points
        self.min_turnaround = 0.0
        # The minimum turnaround time for non-joined points
        self.min_interval = 0.0
        # If we are currently loading then block loading more points
        self.loading = False
        # Where we have generated into profile
        self.end_index = 0
        # Where we should stop loading points
        self.steps_up_to = 0
        # What sort of triggers to output
        self.output_triggers: Optional[MotionTrigger] = None
        # Profile points that haven't been sent yet
        # {timeArray/velocityMode/userPrograms/a/b/c/u/v/w/x/y/z: [elements]}
        self.profile: Dict[str, List] = {}
        # accumulated intervals since the last PVT point used by sparse
        # trajectory logic
        self.time_since_last_pvt = 0
        # Stored generator for positions
        self.generator: CompoundGenerator = None

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ValidateHook, self.on_validate)
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
        registrar.hook(
            (scanning.hooks.AbortHook, scanning.hooks.PauseHook), self.on_abort
        )

    def notify_dispatch_request(self, request: Request) -> None:
        if isinstance(request, Put) and request.path[1] == "design":
            # We have hooked self.reload to PreConfigure, and reload() will
            # set design attribute, so explicitly allow this without checking
            # it is in no_save (as it won't be in there)
            pass
        else:
            super().notify_dispatch_request(request)

    @add_call_types
    def on_reset(self, context: builtin.hooks.AContext) -> None:
        super().on_reset(context)
        self.on_abort(context)

    # Allow CamelCase as arguments will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def on_validate(
        self,
        context: scanning.hooks.AContext,
        generator: scanning.hooks.AGenerator,
        axesToMove: scanning.hooks.AAxesToMove,
        part_info: scanning.hooks.APartInfo,
    ) -> scanning.hooks.UParameterTweakInfos:
        child = context.block_view(self.mri)
        # Check that we can move all the requested axes
        available = set(child.layout.value.name)
        motion_axes = get_motion_axes(generator, axesToMove)
        assert available.issuperset(motion_axes), (
            "Some of the requested axes %s are not on the motor list %s"
            % (list(axesToMove), sorted(available))
        )
        # If GPIO not demanded for every point we don't need to align to the
        # servo cycle
        trigger = get_motion_trigger(part_info)
        if trigger != scanning.infos.MotionTrigger.EVERY_POINT:
            return None
        # Find the duration
        assert generator.duration > 0, "Can only do fixed duration at the moment"
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
        else:
            return None

    def move_to_start(self, child: Block, cs_port: str, completed_steps: int) -> Future:
        # Work out what method to call
        match = re.search(r"\d+$", cs_port)
        assert match, "Cannot extract CS number from CS port '%s'" % cs_port
        move_async = child["moveCS%s_async" % match.group()]
        # Set all the axes to move to the start positions
        first_point = self.generator.get_point(completed_steps)
        args = {}
        move_to_start_time = 0.0
        for axis_name, velocity in point_velocities(
            self.axis_mapping, first_point
        ).items():
            motor_info: MotorInfo = self.axis_mapping[axis_name]
            acceleration_distance = motor_info.ramp_distance(
                0, velocity, min_ramp_time=MIN_TIME
            )
            start_pos = first_point.lower[axis_name] - acceleration_distance
            args[motor_info.cs_axis.lower()] = start_pos
            # Time profile that the move is likely to take
            # NOTE: this is only accurate if pmac max velocity in linear motion
            # prog is set to same speed as motor record VMAX
            profile = motor_info.make_velocity_profile(
                0, 0, motor_info.current_position - start_pos, 0
            )
            times, _ = profile.make_arrays()
            move_to_start_time = max(times[-1], move_to_start_time)
        # Call the method with the values
        fs = move_async(moveTime=move_to_start_time, **args)
        return fs

    # Allow CamelCase as arguments will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def on_configure(
        self,
        context: scanning.hooks.AContext,
        completed_steps: scanning.hooks.ACompletedSteps,
        steps_to_do: scanning.hooks.AStepsToDo,
        part_info: scanning.hooks.APartInfo,
        generator: scanning.hooks.AGenerator,
        axesToMove: scanning.hooks.AAxesToMove,
    ) -> None:
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
        infos: List[MinTurnaroundInfo] = scanning.infos.MinTurnaroundInfo.filter_values(
            part_info
        )
        if infos:
            assert len(infos) == 1, "Expected 0 or 1 MinTurnaroundInfos, got %d" % len(
                infos
            )
            self.min_turnaround = max(MIN_TIME, infos[0].gap)
            self.min_interval = infos[0].interval
        else:
            self.min_turnaround = MIN_TIME
            self.min_interval = MIN_INTERVAL

        # Work out the cs_port we should be using
        layout_table = child.layout.value
        if motion_axes:
            self.axis_mapping = cs_axis_mapping(context, layout_table, motion_axes)
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
        child.writeProfile(
            csPort=cs_port,
            timeArray=[MIN_TIME],
            userPrograms=[UserPrograms.ZERO_PROGRAM],
        )
        child.executeProfile()
        fs: Union[List, Future]
        if motion_axes:
            # Start off the move to the start
            fs = self.move_to_start(child, cs_port, completed_steps)
        else:
            fs = []
        # Set how far we should be going and the completed steps lookup
        self.steps_up_to = completed_steps + steps_to_do
        self.completed_steps_lookup = []
        # Reset the profiles that still need to be sent
        self.profile = dict(timeArray=[], velocityMode=[], userPrograms=[],)
        self.time_since_last_pvt = 0
        for info in self.axis_mapping.values():
            self.profile[info.cs_axis.lower()] = []
        self.calculate_generator_profile(completed_steps, do_run_up=True)
        self.write_profile_points(child, cs_port)
        # Wait for the motors to have got to the start
        context.wait_all_futures(fs)

    @add_call_types
    def on_run(self, context: scanning.hooks.AContext) -> None:
        if self.generator:
            self.loading = False
            child = context.block_view(self.mri)
            # Wait for the trajectory to run and complete
            child.pointsScanned.subscribe_value(self.update_step, child)
            # TODO: we should return at the end of the last point for PostRun
            child.executeProfile()

    @add_call_types
    def on_abort(self, context: scanning.hooks.AContext) -> None:
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
            self.registrar.report(scanning.infos.RunProgressInfo(completed_steps))
            # Keep PROFILE_POINTS trajectory points in front
            if (
                not self.loading
                and self.end_index < self.steps_up_to
                and len(self.completed_steps_lookup) - scanned < PROFILE_POINTS
            ):
                self.loading = True
                self.calculate_generator_profile(self.end_index)
                self.write_profile_points(child)
                self.loading = False

            # If we got to the end, there might be some leftover points that
            # need to be appended to finish
            if (
                not self.loading
                and self.end_index == self.steps_up_to
                and self.profile["timeArray"]
            ):
                self.loading = True
                self.calculate_generator_profile(self.end_index)
                self.write_profile_points(child)
                assert not self.profile["timeArray"], (
                    "Why do we still have points? %s" % self.profile
                )
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
                    overflow += ticks % 1
                    ticks = int(ticks)
                    if overflow > 0.5:
                        overflow -= 1
                        ticks += 1
                    time_array_ticks.append(ticks)
                # TODO: overflow discarded every 10000 points, is it a problem?
                v = np.array(time_array_ticks, np.int32)
            elif k in ("velocityMode", "userPrograms"):
                v = np.array(v, np.int32)
            else:
                v = np.array(v, np.float64)
            args[k] = v

        child.writeProfile(**args)

    user_program = {
        scanning.infos.MotionTrigger.NONE: {
            PointType.POINT_JOIN: UserPrograms.NO_PROGRAM,
            PointType.START_OF_ROW: UserPrograms.NO_PROGRAM,
            PointType.MID_POINT: UserPrograms.NO_PROGRAM,
            PointType.END_OF_ROW: UserPrograms.NO_PROGRAM,
            PointType.TURNAROUND: UserPrograms.NO_PROGRAM,
        },
        scanning.infos.MotionTrigger.ROW_GATE: {
            PointType.POINT_JOIN: UserPrograms.NO_PROGRAM,
            PointType.START_OF_ROW: UserPrograms.LIVE_PROGRAM,
            PointType.MID_POINT: UserPrograms.NO_PROGRAM,
            PointType.END_OF_ROW: UserPrograms.ZERO_PROGRAM,
            PointType.TURNAROUND: UserPrograms.NO_PROGRAM,
        },
        scanning.infos.MotionTrigger.EVERY_POINT: {
            PointType.POINT_JOIN: UserPrograms.LIVE_PROGRAM,
            PointType.START_OF_ROW: UserPrograms.LIVE_PROGRAM,
            PointType.MID_POINT: UserPrograms.MID_PROGRAM,
            PointType.END_OF_ROW: UserPrograms.DEAD_PROGRAM,
            PointType.TURNAROUND: UserPrograms.ZERO_PROGRAM,
        },
    }

    def get_user_program(self, point_type: PointType) -> int:
        assert self.output_triggers, "No output triggers"
        return self.user_program[self.output_triggers][point_type]

    def calculate_profile_from_velocities(
        self, time_arrays, velocity_arrays, current_positions, completed_steps
    ):
        # at this point we have time/velocity arrays with 2-4 values for each
        # axis. Each time represents a (instantaneous) change in acceleration.
        # We want to translate this into a move profile (time/position).
        # Every axis profile must have a point for each of the times from
        # all axes combined

        # extract the time points from all axes
        t_list = []
        for time_array in time_arrays.values():
            t_list.extend(time_array)
        combined_times = np.array(t_list)
        combined_times = np.unique(combined_times)
        # remove the 0 time initial point
        combined_times = list(np.sort(combined_times))[1:]
        num_intervals = len(combined_times)

        # set up the time, mode and user arrays for the trajectory
        prev_time = 0
        time_intervals = []
        for t in combined_times:
            # times are absolute - convert to intervals
            time_intervals.append(t - prev_time)
            prev_time = t

        # generate the profile positions in a temporary list of dict:
        turnaround_profile = [{} for n in range(num_intervals)]

        # Do this for each axis' velocity and time arrays
        for axis_name, motor_info in self.axis_mapping.items():
            axis_times = time_arrays[axis_name]
            axis_velocities = velocity_arrays[axis_name]
            prev_velocity = axis_velocities[0]
            position = current_positions[axis_name]
            # tracks the accumulated interpolated interval time since the
            # last axis velocity profile point
            time_interval = 0
            # At this point we have time/velocity arrays with multiple values
            # some of which align with the axis_times and some interleave.
            # We want to create a matching move profile of 'num_intervals'
            axis_pt = 1
            for i in range(num_intervals):
                axis_velocity = axis_velocities[axis_pt]
                axis_prev_velocity = axis_velocities[axis_pt - 1]
                axis_interval = axis_times[axis_pt] - axis_times[axis_pt - 1]

                if np.isclose(combined_times[i], axis_times[axis_pt]):
                    # this combined point matches the axis point
                    # use the axis velocity and move to the next axis point
                    this_velocity = axis_velocities[axis_pt]
                    axis_pt += 1
                    time_interval = 0
                else:
                    # this combined point is between two axis points,
                    # interpolate the velocity between those axis points
                    time_interval += time_intervals[i]
                    fraction = time_interval / axis_interval
                    dv = axis_velocity - axis_prev_velocity
                    this_velocity = axis_prev_velocity + fraction * dv

                part_position = motor_info.ramp_distance(
                    prev_velocity, this_velocity, time_intervals[i]
                )
                prev_velocity = this_velocity

                position += part_position
                turnaround_profile[i][axis_name] = position

        user_program = self.get_user_program(PointType.TURNAROUND)
        for i in range(num_intervals):
            self.add_profile_point(
                time_intervals[i],
                VelocityModes.REAL_PREV_TO_CURRENT,
                user_program,
                completed_steps,
                turnaround_profile[i],
            )

    def add_profile_point(
        self, time_point, velocity_mode, user_program, completed_step, axis_points
    ):
        # Add padding if the move time exceeds the max pmac move time
        if time_point > MAX_MOVE_TIME:
            assert self.profile[
                "timeArray"
            ], "Can't stretch the first point of a profile"
            nsplit = int(time_point / MAX_MOVE_TIME + 1)
            for _ in range(nsplit):
                self.profile["timeArray"].append(time_point / nsplit)
            for _ in range(nsplit - 1):
                self.profile["velocityMode"].append(VelocityModes.AVERAGE_PREV_TO_NEXT)
                self.profile["userPrograms"].append(UserPrograms.NO_PROGRAM)
            for k, v in axis_points.items():
                cs_axis = self.axis_mapping[k].cs_axis.lower()
                last_point = self.profile[cs_axis][-1]
                per_section = float(v - last_point) / nsplit
                for i in range(1, nsplit):
                    self.profile[cs_axis].append(last_point + i * per_section)
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

    def add_generator_point_pair(self, point, point_num, points_are_joined):
        # Add position
        user_program = self.get_user_program(PointType.MID_POINT)
        self.add_profile_point(
            point.duration / 2.0,
            VelocityModes.AVERAGE_PREV_TO_NEXT,
            user_program,
            point_num,
            {name: point.positions[name] for name in self.axis_mapping},
        )

        # insert the lower bound of the next frame
        if points_are_joined:
            user_program = self.get_user_program(PointType.POINT_JOIN)
            velocity_point = VelocityModes.AVERAGE_PREV_TO_NEXT
        else:
            user_program = self.get_user_program(PointType.END_OF_ROW)
            velocity_point = VelocityModes.REAL_PREV_TO_CURRENT

        self.add_profile_point(
            point.duration / 2.0,
            velocity_point,
            user_program,
            point_num + 1,
            {name: point.upper[name] for name in self.axis_mapping},
        )

    def add_sparse_point(self, points, point_num, points_are_joined, same_velocities):
        """
        Add in points but skip those that are linear to create a sparse
        trajectory. Add the upper bound when the points are non-linear.
        Always add the upper bound for the last point in a row (not joined to
        the next point).

        Joined| Same Vel|| Add Point | Add Upper
        0     | 0       || Y         | Y
        0     | 1       || N         | Y
        1     | 0       || Y         | Y
        1     | 1       || N         | N

        NOTE:
        This function may be called millions of times during the configure
        phase and hence is highly optimized. In particular the use of variable
        'point' looks like it may be referenced before assignment. The paths
        controlled by the matrix above show that it will be always be assigned
        or not used at all. Indexing into points[] is expensive so this is
        intentional.
        """
        if self.time_since_last_pvt > 0 and not points_are_joined:
            # assume we can skip if we are at the end of a row and we
            # just skipped the most recent point (i.e. time_since_last_pvt > 0)
            do_skip = True
        else:
            # otherwise skip this point if it is linear to previous point
            do_skip = points_are_joined and same_velocities

        if do_skip:
            self.time_since_last_pvt += points.duration[point_num]
        else:
            # not skipping - add this mid or end point
            point = points[point_num]
            user_program = self.get_user_program(PointType.MID_POINT)
            self.add_profile_point(
                self.time_since_last_pvt + point.duration / 2.0,
                VelocityModes.AVERAGE_PREV_TO_NEXT,
                user_program,
                point_num,
                {name: point.positions[name] for name in self.axis_mapping},
            )
            self.time_since_last_pvt = point.duration / 2.0

        # only add the lower bound if we did not skip this point OR if we are
        # at the end of a row where we always require a final point
        if not do_skip or not points_are_joined:
            # insert the lower bound of the next frame (i.e. the upper bound for
            # this frame)
            if points_are_joined:
                user_program = self.get_user_program(PointType.POINT_JOIN)
                velocity_point = VelocityModes.AVERAGE_PREV_TO_NEXT
            else:
                point = points[point_num]
                user_program = self.get_user_program(PointType.END_OF_ROW)
                if self.time_since_last_pvt > 0:
                    # if we have previously skipped points in this row then we
                    # use AVERAGE_PREV_TO_CURRENT at the end of the row this
                    # breaks the continuous line of REAL_PREV_TO_CURRENT which
                    # would accumulate errors over the scan
                    velocity_point = VelocityModes.AVERAGE_PREV_TO_CURRENT
                else:
                    velocity_point = VelocityModes.REAL_PREV_TO_CURRENT

            self.add_profile_point(
                self.time_since_last_pvt,
                velocity_point,
                user_program,
                point_num + 1,
                {name: point.upper[name] for name in self.axis_mapping},
            )
            self.time_since_last_pvt = 0

    def get_some_points(self, start_index):
        # calculate the indices of the next batch of points to get for
        # the calculate_generator_profile loop
        # cap at PROFILE_POINTS (+1 so we can always get next_point)
        if start_index == self.steps_up_to:
            return None, None, None
        if self.steps_up_to - start_index > BATCH_POINTS:
            up_to = BATCH_POINTS + start_index + 1
            points = self.generator.get_points(start_index, up_to)
        else:
            points = self.generator.get_points(start_index, self.steps_up_to)

        velocities = all_points_same_velocities(points)
        joined = all_points_joined(points)

        return points, joined, velocities

    def calculate_generator_profile(self, start_index, do_run_up=False):
        # If we are doing the first build, do_run_up will be passed to flag
        # that we need a run up, else just continue from the previous point
        if do_run_up:
            point = self.generator.get_point(start_index)

            # Calculate how long to leave for the run-up (at least MIN_TIME)
            run_up_time = self.min_interval
            axis_points = {}
            for axis_name, velocity in point_velocities(
                self.axis_mapping, point
            ).items():
                axis_points[axis_name] = point.lower[axis_name]
                motor_info = self.axis_mapping[axis_name]
                run_up_time = max(
                    run_up_time, motor_info.acceleration_time(0, velocity)
                )

            # Add lower bound
            user_program = self.get_user_program(PointType.START_OF_ROW)
            self.add_profile_point(
                run_up_time,
                VelocityModes.REAL_PREV_TO_CURRENT,
                user_program,
                start_index,
                axis_points,
            )

        self.time_since_last_pvt = 0

        points, joined, velocities = self.get_some_points(start_index)
        points_idx = start_index
        for i in range(start_index, self.steps_up_to):
            if i - points_idx >= BATCH_POINTS:
                points, joined, velocities = self.get_some_points(i)
                points_idx = i

            last_point = i + 1 == self.steps_up_to
            if not last_point:
                # cope with the zero axes case (where joined == None)
                points_are_joined = joined is None or joined[i - points_idx]
                same_velocities = velocities is None or velocities[i - points_idx]
            else:
                same_velocities = points_are_joined = False

            if self.output_triggers == scanning.infos.MotionTrigger.EVERY_POINT:
                self.add_generator_point_pair(
                    points[i - points_idx], i, points_are_joined
                )
            else:
                self.add_sparse_point(
                    points, i - points_idx, points_are_joined, same_velocities
                )

            # add in the turnaround between non-contiguous points
            if not (points_are_joined or last_point):
                self.insert_gap(
                    points[i - points_idx], points[i - points_idx + 1], i + 1
                )

            # Check if we have exceeded the points number and need to write
            # Strictly less than so we always add one more point to the time
            # array so we can always stretch points in a subsequent add with
            # the values already in the profiles
            if len(self.profile["timeArray"]) > PROFILE_POINTS:
                self.end_index = i + 1
                return

        self.add_tail_off()

    def add_tail_off(self):
        # Add the last tail off point
        point = self.generator.get_point(self.steps_up_to - 1)
        # Calculate how long to leave for the tail-off
        # #(at least MIN_TIME)
        axis_points = {}
        tail_off_time = self.min_interval
        for axis_name, velocity in point_velocities(
            self.axis_mapping, point, entry=False
        ).items():
            motor_info = self.axis_mapping[axis_name]
            tail_off_time = max(
                tail_off_time, motor_info.acceleration_time(0, velocity)
            )
            tail_off = motor_info.ramp_distance(velocity, 0)
            axis_points[axis_name] = point.upper[axis_name] + tail_off
        # Do the last move
        user_program = self.get_user_program(PointType.TURNAROUND)
        self.add_profile_point(
            tail_off_time,
            VelocityModes.ZERO_VELOCITY,
            user_program,
            self.steps_up_to,
            axis_points,
        )
        self.end_index = self.steps_up_to

    def insert_gap(self, point, next_point, completed_steps):
        # Work out the velocity profiles of how to move to the start
        min_turnaround = max(self.min_turnaround, point.delay_after)
        time_arrays, velocity_arrays = profile_between_points(
            self.axis_mapping, point, next_point, min_turnaround, self.min_interval
        )

        start_positions = {}
        for axis_name in self.axis_mapping:
            start_positions[axis_name] = point.upper[axis_name]

        # Work out the Position trajectories from these profiles
        self.calculate_profile_from_velocities(
            time_arrays, velocity_arrays, start_positions, completed_steps
        )

        # make sure the last point is the same as next_point.lower since
        # calculate_profile_from_velocities fails when the turnaround is 2
        # points only
        for axis_name, motor_info in self.axis_mapping.items():
            self.profile[motor_info.cs_axis.lower()][-1] = next_point.lower[axis_name]

        # Change the last point to be a live frame
        self.profile["velocityMode"][-1] = VelocityModes.REAL_PREV_TO_CURRENT
        user_program = self.get_user_program(PointType.START_OF_ROW)
        self.profile["userPrograms"][-1] = user_program
