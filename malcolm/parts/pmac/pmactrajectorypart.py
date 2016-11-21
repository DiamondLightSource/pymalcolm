from collections import Counter

import numpy as np
from scanpointgenerator import FixedDurationMutator, CompoundGenerator

from malcolm.controllers.runnablecontroller import RunnableController, \
    ParameterTweakInfo
from malcolm.core import method_takes, REQUIRED, Info
from malcolm.core.vmetas import StringArrayMeta, PointGeneratorMeta
from malcolm.parts.builtin.childpart import ChildPart

# Number of seconds that a trajectory tick is
TICK_S = 0.000001

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

# How many generator points to load each time
POINTS_PER_BUILD = 4000

# All possible PMAC CS axis assignment
cs_axis_names = list("ABCUVWXYZ")

# Servo frequency
I10 = 1705244
SERVO_FREQ = 8388608000. / I10

# Args for configure and validate
configure_args = [
    "generator", PointGeneratorMeta("Generator instance"), REQUIRED,
    "axesToMove", StringArrayMeta(
        "List of axes in inner dimension of generator that should be moved"),
    []]

# Class for these motor variables
class MotorInfo(Info):
    def __init__(self, cs_axis, cs_port, acceleration_time, resolution, offset,
                 max_velocity, current_position, scannable):
        self.cs_axis = cs_axis
        self.cs_port = cs_port
        self.acceleration_time = acceleration_time
        self.resolution = resolution
        self.offset = offset
        self.max_velocity = max_velocity
        self.current_position = current_position
        self.scannable = scannable


class PMACTrajectoryPart(ChildPart):
    # Axis information stored from validate
    # {scannable_name: MotorInfo}
    axis_mapping = None
    # CS asyn port name to do trajectory on
    cs_port = None
    # Lookup of the completed_step value for each point
    completed_steps_lookup = []
    # If we are currently loading then block loading more points
    loading = False
    # The last index we have loaded
    end_index = 0
    # Where we should stop loading points
    steps_up_to = 0
    # Stored generator for positions
    generator = None

    @RunnableController.Reset
    def reset(self, task):
        super(PMACTrajectoryPart, self).reset(task)
        self.abort(task)

    @RunnableController.Validate
    @method_takes(*configure_args)
    def validate(self, task, part_info, params):
        self._make_axis_mapping(part_info, params.axesToMove)
        # Find the last FixedDurationMutator
        mutators = []
        fdm = None
        for mutator in params.generator.mutators:
            if isinstance(mutator, FixedDurationMutator):
                fdm = mutator
            else:
                mutators.append(mutator)
        # convert to multiple of servo ticks, rounding down
        ticks = np.floor(SERVO_FREQ * fdm.duration)
        # convert to integer number of microseconds, rounding up
        micros = np.ceil(ticks / SERVO_FREQ * 1e6)
        # back to duration
        duration = float(micros) / 1e6
        if duration != fdm.duration:
            new_generator = CompoundGenerator(
                generators=params.generator.generators,
                excluders=params.generator.excluders,
                mutators=mutators + [FixedDurationMutator(duration)])
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
        missing = set(axes_to_move) - set(axis_mapping)
        assert not missing, \
            "Some scannables %s are not children of this controller" % missing
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
    @RunnableController.PostRunReady
    @RunnableController.Seek
    @method_takes(*configure_args)
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        self.generator = params.generator
        self.cs_port, self.axis_mapping = self._make_axis_mapping(
            part_info, params.axesToMove)
        futures = self.move_to_start(task, completed_steps)
        self.steps_up_to = completed_steps + steps_to_do
        self.completed_steps_lookup = []
        profile = self.build_generator_profile(completed_steps)
        task.wait_all(futures)
        self.write_profile_points(task, **profile)
        # Max size of array
        task.put(self.child["numPoints"], self.generator.num * 3)
        task.post(self.child["buildProfile"])

    @RunnableController.Run
    @RunnableController.Resume
    def run(self, task, update_completed_steps):
        self.loading = False
        task.subscribe(self.child["pointsScanned"], self.update_step,
                       update_completed_steps, task)
        task.post(self.child["executeProfile"])

    @RunnableController.Abort
    @RunnableController.Pause
    def abort(self, task):
        task.post(self.child["abortProfile"])

    def get_move_time(self, axis_name, demand, current=None):
        motor_info = self.axis_mapping[axis_name]
        if current is None:
            current = motor_info.current_position
        dist = float(abs(demand - current))
        accl_time = float(motor_info.acceleration_time)
        accl_dist = accl_time * motor_info.max_velocity
        if dist < accl_dist:
            time = np.sqrt(accl_time * dist / motor_info.max_velocity)
        else:
            full_speed_dist = dist - accl_dist
            time = accl_time * 2 + full_speed_dist / motor_info.max_velocity
        return time

    def update_step(self, scanned, update_completed_steps, task):
        if scanned > 0:
            completed_steps = self.completed_steps_lookup[scanned - 1]
            update_completed_steps(completed_steps, self)
            if not self.loading and self.end_index < self.steps_up_to and \
                    self.end_index - completed_steps < POINTS_PER_BUILD:
                self.loading = True
                profile = self.build_generator_profile(
                    self.end_index, do_run_up=False)
                self.write_profile_points(task, **profile)
                task.post(self.child["appendProfile"])
                self.loading = False

    def run_up_positions(self, point):
        """Generate a dict of axis run up distances given a time

        Args:
            point (Point): The first point of the scan
            fraction (float): The fraction of the Point exposure time that the
                run up move should take
        """
        positions = {}

        for axis_name, motor_info in self.axis_mapping.items():
            full_distance = point.upper[axis_name] - point.lower[axis_name]
            velocity = full_distance / point.duration
            # Divide by 2 as we are decelerating to zero
            accl_dist = motor_info.acceleration_time * velocity * 0.5
            positions[axis_name] = accl_dist

        return positions

    def calculate_acceleration_time(self):
        acceleration_time = max(
            info.acceleration_time for info in self.axis_mapping.values())
        return acceleration_time

    def move_to_start(self, task, start_index):
        """Move to the run up position ready to start the scan"""
        acceleration_time = self.calculate_acceleration_time()
        first_point = self.generator.get_point(start_index)
        trajectory = {}
        move_time = 0.0

        for axis_name, run_up in self.run_up_positions(first_point).items():
            start_pos = first_point.lower[axis_name] - run_up
            trajectory[axis_name] = [start_pos]
            move_time = max(move_time, self.get_move_time(axis_name, start_pos))

        if move_time < 0.01:
            # Don't have to move anywhere
            return []

        # if we are spending any time at max_velocity, put in points at
        # the acceleration times
        if move_time > 2 * acceleration_time:
            time_array = [acceleration_time, move_time - 2 * acceleration_time,
                          acceleration_time]
            velocity_mode = [CURRENT_TO_NEXT, PREV_TO_CURRENT, ZERO_VELOCITY]
            user_programs = [NO_PROGRAM, NO_PROGRAM, TRIG_ZERO]
            for axis_name, positions in trajectory.items():
                motor_info = self.axis_mapping[axis_name]
                start_pos = positions[0]
                dist = start_pos - motor_info.current_position
                velocity = dist / (move_time - motor_info.acceleration_time)
                accl_dist = acceleration_time * velocity / 2
                positions.insert(0, motor_info.current_position + accl_dist)
                positions.insert(1, start_pos - accl_dist)
        else:
            time_array = [move_time]
            velocity_mode = [ZERO_VELOCITY]
            user_programs = [TRIG_ZERO]

        self.write_profile_points(task, time_array, velocity_mode, trajectory,
                                  user_programs)
        task.post(self.child["buildProfile"])
        futures = task.post_async(self.child["executeProfile"])
        return futures

    def write_profile_points(self, task, time_array, velocity_mode, trajectory,
                             user_programs):
        """Build profile using part_tasks

        Args:
            time_array (list): List of times in ms
            velocity_mode (list): List of velocity modes like PREV_TO_NEXT
            trajectory (dict): {axis_name: [positions in EGUs]}
            task (Task): Task for running
            user_programs (list): List of user programs like TRIG_LIVE_FRAME
        """
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
        task.put_many(self.child, attr_dict)

        # Start adding points, padding if the move time exceeds 4s
        i = 0
        while i < len(time_array):
            t = time_array[i]
            if t > 4:
                # split
                nsplit = int(t / 4.0 + 1)
                new_time_array = time_array[:i]
                new_velocity_mode = velocity_mode[:i]
                new_user_programs = user_programs[:i]
                for _ in range(nsplit):
                    new_time_array.append(t / nsplit)
                    new_velocity_mode.append(PREV_TO_NEXT)
                    new_user_programs.append(NO_PROGRAM)
                time_array = new_time_array + time_array[i+1:]
                user_programs = new_user_programs[:-1] + user_programs[i:]
                velocity_mode = new_velocity_mode[:-1] + velocity_mode[i:]

                for k, traj in trajectory.items():
                    new_traj = traj[:i]
                    per_section = float(traj[i] - traj[i-1]) / nsplit
                    for j in range(1, nsplit+1):
                        new_traj.append(traj[i-1] + j * per_section)
                    trajectory[k] = new_traj + traj[i+1:]

                i += nsplit
            else:
                i += 1

        # Process the time in ticks
        overflow = 0
        time_array_ticks = []
        for t in time_array:
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
            velocityMode=velocity_mode,
            userPrograms=user_programs,
            pointsToBuild=len(time_array)
        )
        for axis_name in trajectory:
            motor_info = self.axis_mapping[axis_name]
            cs_axis = motor_info.cs_axis
            attr_dict["positions%s" % cs_axis] = trajectory[axis_name]
        task.put_many(self.child, attr_dict)

    def build_generator_profile(self, start_index, do_run_up=True):
        acceleration_time = self.calculate_acceleration_time()
        trajectory = {axis_name: [] for axis_name in self.axis_mapping}
        time_array = []
        velocity_mode = []
        user_programs = []

        # Cap last point to steps_up_to
        self.end_index = start_index + POINTS_PER_BUILD
        if self.end_index > self.steps_up_to:
            self.end_index = self.steps_up_to

        # If we are doing the first build, do_run_up will be called so flag
        # that we need a runup, else just continue from the previous point
        if do_run_up:
            point = self.generator.get_point(start_index)
            # Add lower bound
            time_array.append(acceleration_time)
            velocity_mode.append(CURRENT_TO_NEXT)
            user_programs.append(TRIG_LIVE_FRAME)
            self.completed_steps_lookup.append(0)
            for axis_name, positions in trajectory.items():
                positions.append(point.lower[axis_name])

        for i in range(start_index, self.end_index):
            point = self.generator.get_point(i)

            # Add position
            time_array.append(point.duration / 2.0)
            velocity_mode.append(PREV_TO_NEXT)
            user_programs.append(TRIG_CAPTURE)
            self.completed_steps_lookup.append(i)
            for axis_name, positions in trajectory.items():
                positions.append(point.positions[axis_name])

            # Add upper bound
            time_array.append(point.duration / 2.0)
            velocity_mode.append(PREV_TO_NEXT)
            user_programs.append(TRIG_LIVE_FRAME)
            self.completed_steps_lookup.append(i + 1)
            for axis_name, positions in trajectory.items():
                positions.append(point.upper[axis_name])

            # Check if we need to insert the upper bound point
            if i + 1 < self.end_index:
                next_point = self.generator.get_point(i + 1)
                lower_move_time, turnaround_midpoint = \
                    self.need_lower_move_time(point, next_point)

                # Check if we need a turnaround midpoint
                if lower_move_time:
                    # Change last point to be dead frame
                    velocity_mode[-1] = PREV_TO_CURRENT
                    user_programs[-1] = TRIG_DEAD_FRAME

                    # Add a padding point
                    time_array.append(lower_move_time)
                    velocity_mode.append(PREV_TO_NEXT)
                    user_programs.append(TRIG_ZERO)
                    self.completed_steps_lookup.append(i + 1)
                    for axis_name, positions in trajectory.items():
                        positions.append(turnaround_midpoint[axis_name])

                    # Add lower bound
                    time_array.append(lower_move_time)
                    velocity_mode.append(CURRENT_TO_NEXT)
                    user_programs.append(TRIG_LIVE_FRAME)
                    self.completed_steps_lookup.append(i + 1)
                    for axis_name, positions in trajectory.items():
                        positions.append(next_point.lower[axis_name])

        # Add the last tail off point
        if self.end_index == self.steps_up_to:
            point = self.generator.get_point(self.end_index - 1)

            time_array.append(acceleration_time)
            velocity_mode[-1] = PREV_TO_CURRENT
            velocity_mode.append(ZERO_VELOCITY)
            user_programs[-1] = TRIG_DEAD_FRAME
            user_programs.append(TRIG_ZERO)
            self.completed_steps_lookup.append(self.end_index)

            for axis_name, tail_off in self.run_up_positions(point).items():
                positions = trajectory[axis_name]
                positions.append(positions[-1] + tail_off)

        profile = dict(time_array=time_array, velocity_mode=velocity_mode,
                       trajectory=trajectory, user_programs=user_programs)
        return profile

    def _same_sign(self, a, b):
        return a*b >= 0

    def need_lower_move_time(self, last_point, point):
        gap = False
        # Check for axes that need to move within the space between points
        for axis_name, motor_info in self.axis_mapping.items():
            if last_point.upper[axis_name] != point.lower[axis_name]:
                gap = True
                break

        if not gap:
            # No lower move time
            return None, None

        # First point needs to insert lower bound point
        lower_move_time = 0
        turnaround_midpoint = {}
        run_ups = self.run_up_positions(point)

        # If an axis needs to move, then blend moves, otherwise do a move
        # for that axis
        for axis_name, motor_info in self.axis_mapping.items():
            first = last_point.upper[axis_name]
            second = point.lower[axis_name]
            first_distance = last_point.upper[axis_name] - \
                             last_point.lower[axis_name]
            second_distance = point.upper[axis_name] - point.lower[axis_name]
            # If points are different then add in a midpoint
            if first != second:
                turnaround_midpoint[axis_name] = (second - first) * 0.5 + first
                move_time = self.get_move_time(axis_name, second, first)
                lower_move_time = max(lower_move_time, move_time * 0.5)
            # If points are same and direction is different then reverse
            elif not self._same_sign(first_distance, second_distance):
                turnaround_midpoint[axis_name] = second - run_ups[axis_name]
                lower_move_time = max(
                    lower_move_time, motor_info.acceleration_time)

        return lower_move_time, turnaround_midpoint
