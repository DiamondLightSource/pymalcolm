# Treat all division as float division even in python2
from __future__ import division

import numpy as np
from scanpointgenerator import CompoundGenerator
from annotypes import add_call_types, TYPE_CHECKING, Anno

from malcolm.core import config_tag, NumberMeta, PartRegistrar, Widget
from malcolm.modules import builtin, scanning
from malcolm.modules.builtin.parts import ChildPart
from ..infos import MotorInfo, ControllerInfo
from malcolm.modules.pmac.infos import cs_axis_names

if TYPE_CHECKING:
    from typing import Dict, List, Tuple

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

# GPIO triggers, 1 indexed
GPIO_LIVE_FRAME = 1
GPIO_DEAD_FRAME = 2
GPIO_CAPTURE = 3

# Map requested GPIO 1..3 settings to a user program
NO_PROGRAM = 0  # Do nothing
GPIO_PROGRAMS = {
    (1, 0, 0): 1,
    (0, 1, 0): 2,
    (1, 1, 0): 3,
    (0, 0, 1): 4,
    (1, 0, 1): 5,
    (0, 1, 1): 6,
    (1, 1, 1): 7,
    (0, 0, 0): 8,
}  # type: Dict[Tuple[int, int, int], int]

# How many profile points to write each time
PROFILE_POINTS = 10000


with Anno("Initial value for min time for any gaps between frames"):
    AMinTurnaround = float


class PmacTrajectoryPart(ChildPart):
    def __init__(self,
                 name,  # type: builtin.parts.APartName
                 mri,  # type: builtin.parts.AMri
                 initial_min_turnaround=0.0  # type: AMinTurnaround
                 ):
        # type: (...) -> None
        super(PmacTrajectoryPart, self).__init__(
            name, mri, initial_visibility=True)
        # Axis information stored from validate
        self.axis_mapping = None  # type: Dict[str, MotorInfo]
        # Lookup of the completed_step value for each point
        self.completed_steps_lookup = []  # type: List[int]
        # If we are currently loading then block loading more points
        self.loading = False
        # Where we have generated into profile
        self.end_index = 0
        # Where we should stop loading points
        self.steps_up_to = 0
        # Profile points that haven't been sent yet
        # {time_array/velocity_mode/trajectory/user_programs: [elements]}
        self.profile = {}
        # Stored generator for positions
        self.generator = None  # type: CompoundGenerator
        # Last GPIO user program run
        self.last_gpio = None  # type: Tuple[int, int, int]
        # Attribute info
        self.min_turnaround = NumberMeta(
            "float64", "Min time for any gaps between frames",
            tags=[Widget.TEXTINPUT.tag(), config_tag()]
        ).create_attribute_model(initial_min_turnaround)
        # Hooks
        self.register_hooked(scanning.hooks.ValidateHook, self.validate)
        self.register_hooked((scanning.hooks.ConfigureHook,
                              scanning.hooks.PostRunArmedHook,
                              scanning.hooks.SeekHook), self.configure)
        self.register_hooked((scanning.hooks.RunHook,
                              scanning.hooks.ResumeHook), self.run)
        self.register_hooked((scanning.hooks.AbortHook,
                              scanning.hooks.PauseHook), self.abort)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(PmacTrajectoryPart, self).setup(registrar)
        registrar.add_attribute_model("minTurnaround", self.min_turnaround,
                                      self.min_turnaround.set_value)

    @add_call_types
    def reset(self, context):
        # type: (builtin.hooks.AContext) -> None
        super(PmacTrajectoryPart, self).reset(context)
        self.abort(context)

    # Allow CamelCase as arguments will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def validate(self,
                 part_info,  # type: scanning.hooks.APartInfo
                 generator,  # type: scanning.hooks.AGenerator
                 axesToMove,  # type: scanning.hooks.AAxesToMove
                 ):
        # type: (...) -> scanning.hooks.UParameterTweakInfos
        # Make an axis mapping just to check they are all in the same CS
        MotorInfo.cs_axis_mapping(part_info, axesToMove)
        # Find the duration
        assert generator.duration > 0, \
            "Can only do fixed duration at the moment"
        controller_info = ControllerInfo.filter_single_value(part_info)
        servo_freq = controller_info.servo_freq()
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
            serialized["duration"] = duration
            new_generator = CompoundGenerator.from_dict(serialized)
            return scanning.infos.ParameterTweakInfo("generator", new_generator)

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
        child.numPoints.put_value(4000000)
        self.generator = generator
        cs_port, self.axis_mapping = MotorInfo.cs_axis_mapping(
            part_info, axesToMove)
        # Work out the "last GPIO program" from the GPIO bits
        controller_info = ControllerInfo.filter_single_value(part_info)
        self.last_gpio = tuple(controller_info.outputs[:3])
        # Set how far we should be going, and the lookup
        self.steps_up_to = completed_steps + steps_to_do
        self.completed_steps_lookup = []
        # Work out which axes should be used
        use = [info.cs_axis for info in self.axis_mapping.values()]
        attr_dict = dict(cs=cs_port)
        for cs_axis in cs_axis_names:
            attr_dict["use%s" % cs_axis] = cs_axis in use
        child.put_attribute_values(attr_dict)
        self.profile = dict(time_array=[], velocity_mode=[], user_programs=[],
                            trajectory={name: [] for name in self.axis_mapping})
        self.calculate_generator_profile(completed_steps, do_run_up=True)
        self.profile = self.write_profile_points(child, **self.profile)
        # Max size of array
        child.buildProfile()

    @add_call_types
    def run(self, context):
        # type: (scanning.hooks.AContext) -> None
        self.loading = False
        child = context.block_view(self.mri)
        child.pointsScanned.subscribe_value(self.update_step, child)
        child.executeProfile()
        # TODO: when should we transition to postRun?
        # Now wait for up to 2*min_delta time to make sure any
        # update_completed_steps come in
        traj_end = len(self.completed_steps_lookup)
        child.when_value_matches("pointsScanned", traj_end, timeout=0.1)

    @add_call_types
    def abort(self, context):
        # type: (scanning.hooks.AContext) -> None
        child = context.block_view(self.mri)
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
                self.profile = self.write_profile_points(child, **self.profile)
                child.appendProfile()
                self.loading = False

            # If we got to the end, there might be some leftover points that
            # need to be appended to finish
            if not self.loading and self.end_index == self.steps_up_to and \
                    self.profile["time_array"]:
                self.loading = True
                self.calculate_generator_profile(self.end_index)
                self.profile = self.write_profile_points(child, **self.profile)
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
        # Cast to np arrays as it saves on the serialization
        attr_dict = dict(
            timeArray=np.array(time_array_ticks, np.int32),
            velocityMode=np.array(velocity_mode[:PROFILE_POINTS], np.int32),
            userPrograms=np.array(user_programs[:PROFILE_POINTS], np.int32),
            pointsToBuild=len(time_array_ticks)
        )
        for axis_name, axis_points in trajectory.items():
            motor_info = self.axis_mapping[axis_name]
            cs_axis = motor_info.cs_axis
            attr_dict["positions%s" % cs_axis] = np.array(
                axis_points[:PROFILE_POINTS], np.float64)
        child.put_attribute_values(attr_dict)
        return profile

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
        self.profile["user_programs"] += [NO_PROGRAM] * num_intervals
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

    def add_profile_point(self, time_point, velocity_point, user_gpio,
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
        if user_gpio:
            user_point = self.toggle_gpio(user_gpio)
        else:
            user_point = NO_PROGRAM
        self.profile["user_programs"].append(user_point)
        self.completed_steps_lookup.append(completed_step)
        for k, v in axis_points.items():
            self.profile["trajectory"][k].append(v)

    def toggle_gpio(self, gpio):
        # type: (int) -> int
        current_gpio = list(self.last_gpio)
        current_gpio[gpio - 1] ^= 1  # toggle given gpio number
        self.last_gpio = tuple(current_gpio)  # type: Tuple[int, int, int]
        program = GPIO_PROGRAMS[self.last_gpio]
        return program

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
                run_up_time, CURRENT_TO_NEXT, GPIO_LIVE_FRAME, start_index,
                axis_points)

        for i in range(start_index, self.steps_up_to):
            point = self.generator.get_point(i)

            # Add position
            self.add_profile_point(
                point.duration / 2.0, PREV_TO_NEXT, GPIO_CAPTURE, i,
                {name: point.positions[name] for name in self.axis_mapping})

            # If there will be more frames, insert next live frame
            if i + 1 < self.steps_up_to:
                # Check if we need to insert the lower bound of next_point
                next_point = self.generator.get_point(i + 1)
                points_joined = self.points_joined(point, next_point)

                if points_joined:
                    user_point = GPIO_LIVE_FRAME
                    velocity_point = PREV_TO_NEXT
                else:
                    user_point = GPIO_DEAD_FRAME
                    velocity_point = PREV_TO_CURRENT

                self.add_profile_point(
                    point.duration / 2.0, velocity_point, user_point, i + 1,
                    {name: point.upper[name] for name in self.axis_mapping})

                if not points_joined:
                    self.insert_gap(point, next_point, i + 1)
            else:
                # No more frames, dead frame to finish
                self.add_profile_point(
                    point.duration / 2.0, PREV_TO_CURRENT, GPIO_DEAD_FRAME,
                    i + 1,
                    {name: point.upper[name] for name in self.axis_mapping})

            # Check if we have exceeded the points number and need to write
            # Strictly less than so we always add one more point to the time
            # array so we can always stretch points in a subsequent add with
            # the values already in the profiles
            if len(self.profile["time_array"]) > PROFILE_POINTS:
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
        self.add_profile_point(tail_off_time, ZERO_VELOCITY, NO_PROGRAM,
                               self.steps_up_to, axis_points)
        self.end_index = self.steps_up_to

    def points_joined(self, point, next_point):
        # Check for axes that need to move within the space between points
        for axis_name, motor_info in self.axis_mapping.items():
            if point.upper[axis_name] != next_point.lower[axis_name]:
                return False
        return True

    def insert_gap(self, point, next_point, completed_steps):
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
                start_velocities, end_velocities, distances,
                self.min_turnaround.value)

        # Work out the Position trajectories from these profiles
        self.calculate_profile_from_velocities(
            time_arrays, velocity_arrays, start_positions, completed_steps)

        # Change the last point to be a live frame
        self.profile["velocity_mode"][-1] = CURRENT_TO_NEXT
        self.profile["user_programs"][-1] = self.toggle_gpio(GPIO_LIVE_FRAME)
