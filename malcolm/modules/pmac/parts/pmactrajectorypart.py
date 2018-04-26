# Treat all division as float division even in python2
from __future__ import division

from collections import Counter

import numpy as np
from scanpointgenerator import CompoundGenerator

from malcolm.core import method_takes, REQUIRED, method_also_takes, TimeoutError
from malcolm.modules.builtin.parts import StatefulChildPart
from malcolm.modules.builtin.vmetas import StringArrayMeta, NumberMeta
from malcolm.modules.pmac.infos import MotorInfo
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.scanning.infos import ParameterTweakInfo
from malcolm.modules.scanpointgenerator.vmetas import PointGeneratorMeta
from malcolm.tags import widget, config

# Number of seconds that a trajectory tick is
TICK_S = 0.000001

# Minimum move time for any move
MIN_TIME = 0.002

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
NO_PROGRAM = 0       # Do nothing
TRIG_CAPTURE = 4     # Capture 1, Frame 0, Detector 0
TRIG_DEAD_FRAME = 2  # Capture 0, Frame 1, Detector 0
TRIG_LIVE_FRAME = 3  # Capture 0, Frame 1, Detector 1
TRIG_ZERO = 8        # Capture 0, Frame 0, Detector 0

# How many profile points to write each time
PROFILE_POINTS = 10000

# All possible PMAC CS axis assignment
cs_axis_names = list("ABCUVWXYZ")

# Args for configure and validate
configure_args = (
    "generator", PointGeneratorMeta("Generator instance"), REQUIRED,
    "axesToMove", StringArrayMeta(
        "List of axes in inner dimension of generator that should be moved"),
    []
)


@method_also_takes(
    "settle", NumberMeta(
        "float64", "Default settle time when axis point is at zero velocity"), 
        0.0)
class PmacTrajectoryPart(StatefulChildPart):
    # Axis information stored from validate
    # {scannable_name: MotorInfo}
    axis_mapping = None
    # Lookup of the completed_step value for each point
    completed_steps_lookup = []
    # If we are currently loading then block loading more points
    loading = False
    # Where we have generated into profile
    end_index = 0
    # Where we should stop loading points
    steps_up_to = 0
    # Profile points that haven't been sent yet
    # {time_array/velocity_mode/trajectory/user_programs: [elements]}
    profile = {}
    # Stored generator for positions
    generator = None
    # Settle time when axis point is at zero velocity
    settle = None

    def create_attribute_models(self):
        for data in super(PmacTrajectoryPart, self).create_attribute_models():
            yield data
        # Create writeable attribute for the minimum time to leave when there
        # is a gap between frames
        meta = NumberMeta(
            "float64", "Settle time when axis point is at zero velocity",
            tags=[widget("textinput"), config()])
        self.settle = meta.create_attribute_model(self.params.settle)
        yield "settle", self.settle, self.settle.set_value

    @RunnableController.Reset
    def reset(self, context):
        super(PmacTrajectoryPart, self).reset(context)
        self.abort(context)
        self.reset_triggers(context)

    @RunnableController.Validate
    @method_takes(*configure_args)
    def validate(self, context, part_info, params):
        self._make_axis_mapping(part_info, params.axesToMove)
        # Find the duration
        child = context.block_view(self.params.mri)
        assert params.generator.duration > 0, \
            "Can only do fixed duration at the moment"
        servo_freq = 8388608000. / child.i10.value
        # convert half an exposure to multiple of servo ticks, rounding down
        ticks = np.floor(servo_freq * 0.5 * params.generator.duration)
        if not np.isclose(servo_freq, 3200):
            # + 0.002 for some observed jitter in the servo frequency if I10
            # isn't a whole number (any frequency apart from 3.2 kHz)
            ticks += 0.002
        # convert to integer number of microseconds, rounding up
        micros = np.ceil(ticks / servo_freq * 1e6)
        # back to duration
        duration = 2 * float(micros) / 1e6
        if duration != params.generator.duration:
            serialized = params.generator.to_dict()
            serialized["duration"] = duration
            new_generator = CompoundGenerator.from_dict(serialized)
            return [ParameterTweakInfo("generator", new_generator)]

    def _make_axis_mapping(self, part_info, axes_to_move):
        cs_ports = set()
        # dict {name: MotorInfo}
        axis_mapping = {}
        for motor_info in MotorInfo.filter_values(part_info):
            if motor_info.scannable in axes_to_move:
                assert motor_info.cs_axis in cs_axis_names, \
                    "Can only scan 1-1 mappings, %r is %r" % \
                    (motor_info.scannable, motor_info.cs_axis)
                cs_ports.add(motor_info.cs_port)
                axis_mapping[motor_info.scannable] = motor_info
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
        return cs_ports.pop(), axis_mapping

    @RunnableController.Configure
    @RunnableController.PostRunArmed
    @RunnableController.Seek
    @method_takes(*configure_args)
    def configure(self, context, completed_steps, steps_to_do, part_info,
                  params):
        context.unsubscribe_all()
        child = context.block_view(self.params.mri)
        child.numPoints.put_value(4000000)
        self.generator = params.generator
        cs_port, self.axis_mapping = self._make_axis_mapping(
            part_info, params.axesToMove)
        # Set the right CS to move
        child.cs.put_value(cs_port)
        self.completed_steps_lookup = []
        self.profile = dict(time_array=[], velocity_mode=[], user_programs=[],
                            trajectory={name: [] for name in self.axis_mapping})
        future = self.move_to_start(child, completed_steps)
        self.steps_up_to = completed_steps + steps_to_do
        self.completed_steps_lookup = []
        self.profile = dict(time_array=[], velocity_mode=[], user_programs=[],
                            trajectory={name: [] for name in self.axis_mapping})
        self.calculate_generator_profile(completed_steps, do_run_up=True)
        context.wait_all_futures(future)
        self.profile = self.write_profile_points(child, **self.profile)
        # Max size of array
        child.buildProfile()

    @RunnableController.Run
    @RunnableController.Resume
    def run(self, context, update_completed_steps):
        self.loading = False
        child = context.block_view(self.params.mri)
        child.pointsScanned.subscribe_value(
            self.update_step, update_completed_steps, child)
        child.executeProfile()
        # Now wait for up to 2*minDelta time to make sure any
        # update_completed_steps come in
        traj_end = len(self.completed_steps_lookup)
        try:
            child.when_value_matches("pointsScanned", traj_end, timeout=0.1)
        except TimeoutError:
            raise ValueError("PMAC %r didn't report %s steps in time" % (
                self.params.mri, traj_end))

    @RunnableController.Abort
    def abort(self, context):
        child = context.block_view(self.params.mri)
        child.abortProfile()

    @RunnableController.Pause
    def pause(self, context):
        self.abort(context)
        context.sleep(0.5)
        self.reset_triggers(context)

    def update_step(self, scanned, update_completed_steps, child):
        if scanned > 0:
            completed_steps = self.completed_steps_lookup[scanned - 1]
            update_completed_steps(completed_steps, self)
            # Keep PROFILE_POINTS trajectory points in front
            if not self.loading and self.end_index < self.steps_up_to and \
                    len(self.completed_steps_lookup) - scanned < PROFILE_POINTS:
                self.loading = True
                self.calculate_generator_profile(self.end_index)
                self.profile = self.write_profile_points(child, **self.profile)
                child.appendProfile()

                # If we got to the end, there might be some leftover points that
                # need to be appended to finish
                if self.end_index == self.steps_up_to and \
                        self.profile["time_array"]:
                    self.profile = self.write_profile_points(
                        child, **self.profile)
                    assert not self.profile["time_array"], \
                        "Why do we still have points? %s" % self.profile
                    child.appendProfile()

                self.loading = False

    def point_velocities(self, point):
        """Find the velocities of each axis over the current point"""
        velocities = {}
        for axis_name, motor_info in self.axis_mapping.items():
            full_distance = point.upper[axis_name] - point.lower[axis_name]
            velocity = full_distance / point.duration
            assert abs(velocity) < motor_info.max_velocity, \
                "Velocity %s invalid for %r with max_velocity %s" % (
                    velocity, axis_name, motor_info.max_velocity)
            velocities[axis_name] = velocity
        return velocities

    def make_consistent_velocity_profiles(self, v1s, v2s, distances,
                                          min_time=MIN_TIME):
        """Make consistent time and velocity arrays for each axis"""
        time_arrays = {}
        velocity_arrays = {}
        iterations = 5
        while iterations > 0:
            for axis_name, motor_info in self.axis_mapping.items():
                time_arrays[axis_name], velocity_arrays[axis_name] = \
                    motor_info.make_velocity_profile(
                        v1s[axis_name], v2s[axis_name], distances[axis_name],
                        min_time)
                assert time_arrays[axis_name][-1] >= min_time or np.isclose(
                        time_arrays[axis_name][-1], min_time), \
                    "Time %s velocity %s for %s takes less time than %s" % (
                        time_arrays[axis_name], velocity_arrays[axis_name],
                        axis_name, min_time)
            new_min_time = max(t[-1] for t in time_arrays.values())
            if np.isclose(new_min_time, min_time):
                # We've got our consistent set
                return time_arrays, velocity_arrays
            else:
                min_time = new_min_time
                iterations -= 1
        raise ValueError("Can't get a consistent time in 5 iterations")

    def move_to_start(self, child, start_index):
        """Move to the run up position ready to start the scan"""
        first_point = self.generator.get_point(start_index)
        zero_velocities = {}
        current_positions = {}
        distances = {}

        for axis_name, velocity in self.point_velocities(first_point).items():
            motor_info = self.axis_mapping[axis_name]
            acceleration_distance = motor_info.ramp_distance(0, velocity)
            zero_velocities[axis_name] = 0
            start_pos = first_point.lower[axis_name] - acceleration_distance
            current_positions[axis_name] = motor_info.current_position
            distances[axis_name] = start_pos - motor_info.current_position

        # Work out the velocity profiles of how to move to the start
        time_arrays, velocity_arrays = self.make_consistent_velocity_profiles(
            zero_velocities, zero_velocities, distances)

        # If the reported move is tiny, we don't have to try and move
        if max(ts[-1] for ts in time_arrays.values()) < 0.01:
            return []

        # Work out the Position trajectories from these velocity profiles
        self.calculate_profile_from_velocities(
            time_arrays, velocity_arrays, current_positions, 0)

        # Write the profiles, checking there are no left over points
        profile = self.write_profile_points(child, **self.profile)
        assert not profile["time_array"], "Leftover points %s" % profile
        child.buildProfile()
        future = child.executeProfile_async()
        return future

    def write_profile_points(self, child, time_array, velocity_mode,
                             user_programs, trajectory):
        """Build profile using given data

        Args:
            child (Block): Child block for running
            time_array (list): List of times in ms
            velocity_mode (list): List of velocity modes like PREV_TO_NEXT
            trajectory (dict): {axis_name: [positions in EGUs]}
            user_programs (list): List of user programs like TRIG_LIVE_FRAME
        """
        # Overflow profiles go here
        profile = dict(
            time_array=time_array[PROFILE_POINTS:],
            velocity_mode=velocity_mode[PROFILE_POINTS:],
            user_programs=user_programs[PROFILE_POINTS:],
            trajectory={k: v[PROFILE_POINTS:] for k, v in trajectory.items()})

        # Work out which axes should be used and set their resolutions and
        # offsets
        use = []
        attr_dict = dict()
        for axis_name in trajectory:
            motor_info = self.axis_mapping[axis_name]
            cs_axis = motor_info.cs_axis
            use.append(cs_axis)
            attr_dict["resolution%s" % cs_axis] = motor_info.resolution
            attr_dict["offset%s" % cs_axis] = motor_info.offset
        for cs_axis in cs_axis_names:
            attr_dict["use%s" % cs_axis] = cs_axis in use
        child.put_attribute_values(attr_dict)

        # Process the time in ticks
        overflow = 0.0
        time_array_ticks = []
        for t in time_array[:PROFILE_POINTS]:
            ticks = t / TICK_S
            overflow += (ticks % 1)
            ticks = int(ticks)
            if overflow > 0.5:
                overflow -= 1
                ticks += 1
            time_array_ticks.append(ticks)

        # Set the trajectories
        attr_dict = dict(
            timeArray=time_array_ticks,
            velocityMode=velocity_mode[:PROFILE_POINTS],
            userPrograms=user_programs[:PROFILE_POINTS],
            pointsToBuild=len(time_array_ticks)
        )
        for axis_name, axis_points in trajectory.items():
            motor_info = self.axis_mapping[axis_name]
            cs_axis = motor_info.cs_axis
            attr_dict["positions%s" % cs_axis] = axis_points[:PROFILE_POINTS]
        child.put_attribute_values(attr_dict)
        return profile

    def reset_triggers(self, context):
        """Just call a Move to the run up position ready to start the scan"""
        child = context.block_view(self.params.mri)
        child.numPoints.put_value(10)
        self.write_profile_points(child,
                                  time_array=[0.1],
                                  velocity_mode=[ZERO_VELOCITY],
                                  user_programs=[TRIG_ZERO],
                                  trajectory={})
        child.buildProfile()
        child.executeProfile()

    def calculate_profile_from_velocities(self, time_arrays, velocity_arrays,
                                          current_positions, completed_steps):
        trajectory = {}

        # Interpolate the velocity arrays at about INTERPOLATE_INTERVAL
        move_time = max(t[-1] for t in time_arrays.values())
        # Make sure there are at least 2 of them
        num_intervals = max(int(np.floor(move_time / INTERPOLATE_INTERVAL)), 2)
        interval = move_time / num_intervals
        self.profile["time_array"] += [interval] * num_intervals
        self.profile["velocity_mode"] += \
            [PREV_TO_NEXT] * (num_intervals - 1) + [CURRENT_TO_NEXT]
        self.profile["user_programs"] += [TRIG_ZERO] * num_intervals
        self.completed_steps_lookup += [completed_steps] * num_intervals

        # Do this for each velocity array
        for axis_name, motor_info in self.axis_mapping.items():
            trajectory[axis_name] = []
            ts = time_arrays[axis_name]
            vs = velocity_arrays[axis_name]
            position = current_positions[axis_name]
            for i in range(num_intervals):
                time = interval * (i + 1)
                # If we have exceeded the current segment, pop it and add it's
                # position in
                if time > ts[1] and not np.isclose(time, ts[1]):
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
                self.profile["trajectory"][axis_name].append(
                    position + part_position)

    def add_profile_point(self, time_point, velocity_point, user_point,
                          completed_step, axis_points):

        # Add padding if the move time exceeds the max pmac move time
        if time_point > MAX_MOVE_TIME:
            assert self.profile["time_array"], \
                "Can't stretch the first point of a profile"
            nsplit = int(time_point / MAX_MOVE_TIME + 1)
            for _ in range(nsplit):
                self.profile["time_array"].append(time_point / nsplit)
            for _ in range(nsplit - 1):
                self.profile["velocity_mode"].append(PREV_TO_NEXT)
                self.profile["user_programs"].append(NO_PROGRAM)
            for k, v in axis_points.items():
                last_point = self.profile["trajectory"][k][-1]
                per_section = float(v - last_point) / nsplit
                for i in range(1, nsplit):
                    self.profile["trajectory"][k].append(
                        last_point + i * per_section)
            last_completed_step = self.completed_steps_lookup[-1]
            for _ in range(nsplit - 1):
                self.completed_steps_lookup.append(last_completed_step)
        else:
            # Add point
            self.profile["time_array"].append(time_point)

        # Set the requested point
        self.profile["velocity_mode"].append(velocity_point)
        self.profile["user_programs"].append(user_point)
        self.completed_steps_lookup.append(completed_step)
        for k, v in axis_points.items():
            self.profile["trajectory"][k].append(v)

    def calculate_generator_profile(self, start_index, do_run_up=False):
        # If we are doing the first build, do_run_up will be passed to flag
        # that we need a run up, else just continue from the previous point
        if do_run_up:
            point = self.generator.get_point(start_index)

            # Calculate how long to leave for the run-up (at least MIN_TIME)
            run_up_time = MIN_TIME
            axis_points = {}
            for axis_name, velocity in self.point_velocities(point).items():
                axis_points[axis_name] = point.lower[axis_name]
                motor_info = self.axis_mapping[axis_name]
                run_up_time = max(run_up_time,
                                  motor_info.acceleration_time(0, velocity))

            # Add lower bound
            self.add_profile_point(
                run_up_time, CURRENT_TO_NEXT, TRIG_LIVE_FRAME, start_index,
                axis_points)

        for i in range(start_index, self.steps_up_to):
            point = self.generator.get_point(i)

            # Add position
            self.add_profile_point(
                point.duration / 2.0, PREV_TO_NEXT, TRIG_CAPTURE, i,
                {name: point.positions[name] for name in self.axis_mapping})

            # If there will be more frames, insert next live frame
            if i + 1 < self.steps_up_to:
                self.add_profile_point(
                    point.duration / 2.0, PREV_TO_NEXT, TRIG_LIVE_FRAME, i + 1,
                    {name: point.upper[name] for name in self.axis_mapping})

                # Check if we need to insert the lower bound of next_point
                next_point = self.generator.get_point(i + 1)

                # Check if we need to insert a gap
                if not self.points_joined(point, next_point):
                    self.insert_gap(point, next_point, i + 1)
            else:
                # No more frames, dead frame to finish
                self.add_profile_point(
                    point.duration / 2.0, PREV_TO_CURRENT, TRIG_DEAD_FRAME,
                    i + 1,
                    {name: point.upper[name] for name in self.axis_mapping})

            # Check if we have exceeded the points number and need to write
            if len(self.profile["time_array"]) >= PROFILE_POINTS:
                self.end_index = i + 1
                return

        # Add the last tail off point
        point = self.generator.get_point(self.steps_up_to - 1)

        # Calculate how long to leave for the tail-off (at least MIN_TIME)
        axis_points = {}
        tail_off_time = MIN_TIME
        for axis_name, velocity in self.point_velocities(point).items():
            motor_info = self.axis_mapping[axis_name]
            tail_off_time = max(tail_off_time,
                                motor_info.acceleration_time(0, velocity))
            tail_off = motor_info.ramp_distance(velocity, 0)
            axis_points[axis_name] = point.upper[axis_name] + tail_off

        # Do the last move
        self.add_profile_point(tail_off_time, ZERO_VELOCITY, TRIG_ZERO,
                               self.steps_up_to, axis_points)
        self.end_index = self.steps_up_to

    def points_joined(self, point, next_point):
        # Check for axes that need to move within the space between points
        for axis_name, motor_info in self.axis_mapping.items():
            if point.upper[axis_name] != next_point.lower[axis_name]:
                return False
        return True

    def insert_gap(self, point, next_point, completed_steps):
        # Change last point to be dead frame
        self.profile["velocity_mode"][-1] = PREV_TO_CURRENT
        self.profile["user_programs"][-1] = TRIG_DEAD_FRAME

        # Work out the start and end velocities for each axis
        start_velocities = self.point_velocities(point)
        end_velocities = self.point_velocities(next_point)
        start_positions = {}
        distances = {}
        for axis_name, motor_info in self.axis_mapping.items():
            start_positions[axis_name] = point.upper[axis_name]
            distances[axis_name] = \
                next_point.lower[axis_name] - point.upper[axis_name]

        # Work out the velocity profiles of how to move to the start
        time_arrays, velocity_arrays = \
            self.make_consistent_velocity_profiles(
                start_velocities, end_velocities, distances)
                
        # If the next point has a zero velocity and told to add a settle time
        # then do so here
        if max(end_velocities.values()) == 0 and self.settle.value:
            for axis_name, a in time_arrays.items():
                # add a time at v=0 self.settle in the future
                a.append(a[-1] + self.settle.value)
                velocity_arrays[axis_name].append(0.0)

        # Work out the Position trajectories from these profiles
        self.calculate_profile_from_velocities(
            time_arrays, velocity_arrays, start_positions, completed_steps)

        # Change the last point to be a live frame
        self.profile["velocity_mode"][-1] = CURRENT_TO_NEXT
        self.profile["user_programs"][-1] = TRIG_LIVE_FRAME
