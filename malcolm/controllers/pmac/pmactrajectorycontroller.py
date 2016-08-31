from collections import Counter, OrderedDict

from malcolm.controllers.builtin.managercontroller import ManagerController
from malcolm.core import Hook, Table
from malcolm.core.vmetas import NumberArrayMeta, TableMeta

PREV_TO_NEXT = 0
PREV_TO_CURRENT = 1
CURRENT_TO_NEXT = 2
# TODO: this should be handled in the motion program
ZERO = 0

cs_axis_names = list("ABCUVWXYZ")

columns = OrderedDict(
    time=NumberArrayMeta("float64", "Time in ms to spend getting to point"))
columns["velocity_mode"] = NumberArrayMeta("uint8", "Velocity mode for point")

for axis in cs_axis_names:
    columns[axis] = NumberArrayMeta(
        "float64", "Position of %s at this point" % axis)
profile_table = TableMeta("Profile time and velocity arrays", columns=columns)

sm = ManagerController.stateMachine


class PMACTrajectoryController(ManagerController):
    ReportCSInfo = Hook()
    BuildProfile = Hook()
    RunProfile = Hook()
    axis_mapping = None
    cs_port = None
    points_built = 0

    def do_validate(self, params):
        self.get_cs_port(params.axes_to_move)
        return params

    def get_cs_port(self, axes_to_move):
        # Get the cs number of these axes
        cs_info_d = self.run_hook(self.ReportCSInfo, self.create_part_tasks())
        cs_ports = set()
        # dict {name: cs_type}
        axis_mapping = {}
        for part_name, report_d in list(cs_info_d.items()):
            if part_name in axes_to_move:
                assert report_d.cs_axis in cs_axis_names, \
                    "Can only scan 1-1 mappings, %r is %r" % \
                    (part_name, report_d.cs_axis)
                cs_ports.add(report_d.cs_port)
                axis_mapping[part_name] = report_d.cs_axis
        missing = set(axes_to_move) - set(axis_mapping)
        assert not missing, \
            "Some scannables %s are not children of this controller" % missing
        assert len(cs_ports) == 1, \
            "Requested axes %s are in multiple CS numbers %s" % (
                axes_to_move, list(cs_ports))
        cs_axis_counts = Counter(axis_mapping.values())
        # Any cs_axis defs that are used for more that one raw motor
        overlap = [k for k, v in cs_axis_counts.items() if v > 1]
        assert not overlap, \
            "CS axis defs %s have more that one raw motor attached" % overlap
        return cs_ports.pop(), axis_mapping

    def do_configure(self, params):
        self.cs_port, self.axis_mapping = self.get_cs_port(params.axes_to_move)
        self.build_start_profile()
        self.run_hook(self.RunProfile, self.part_tasks)
        self.points_built = self.build_generator_profile()

    def do_run(self):
        self.transition(sm.RUNNING, "Waiting for scan to complete")
        self.run_hook(self.RunProfile, self.part_tasks)
        more_to_do = self.points_built < self.currentStep.value - 1
        if more_to_do:
            self.transition(sm.POSTRUN, "Building next stage")
            self.points_built = self.build_generator_profile(self.points_built)
            return self.stateMachine.READY
        else:
            self.transition(sm.POSTRUN, "Finishing run")
            return self.stateMachine.IDLE

    def run_up_positions(self, point, fraction):
        """Generate a dict of axis positions at start of run up

        Args:
            point (Point): The first point of the scan
            fraction (float): The fraction of the Point exposure time that the
                run up move should take
        """
        positions = {}

        for axis_name in self.axis_mapping:
            full_distance = point.upper[axis_name] - point.lower[axis_name]
            run_up = full_distance * fraction
            positions[axis_name] = run_up

        return positions

    def calculate_acceleration_time(self):
        acceleration_time = 0
        for axis_name in self.axis_mapping:
            part = self.parts[axis_name]
            acceleration_time = max(
                acceleration_time, part.get_acceleration_time())
        return acceleration_time

    def build_start_profile(self):
        """Move to the run up position ready to start the scan"""
        acceleration_time = self.calculate_acceleration_time()
        fraction = acceleration_time / self.exposure
        first_point = self.get_point(0)
        trajectory = {}
        move_time = 0

        for axis_name, run_up in \
                self.run_up_positions(first_point, fraction).items():
            trajectory[axis_name] = [first_point.lower[axis_name] - run_up]
            part = self.parts[axis_name]
            move_time = max(move_time, part.get_move_time(run_up))

        time_array = [move_time]
        velocity_mode = [ZERO]
        self.build_profile(time_array, velocity_mode, trajectory)

    def build_profile(self, time_array, velocity_mode, trajectory):
        """Build profile using self.part_tasks

        Args:
            time_array (list): List of times in ms
            velocity_mode (list): List of velocity modes like PREV_TO_NEXT
            trajectory (dict): {axis_name: [positions in EGUs]}
        """
        profile = Table(profile_table)
        profile.time = time_array
        profile.velocity_mode = velocity_mode
        use = []
        resolutions = []
        offsets = []

        for axis_name in trajectory:
            cs_axis = self.axis_mapping[axis_name]
            profile[cs_axis] = trajectory[axis_name]
            use.append(cs_axis)
            resolutions.append(self.parts[axis_name].get_resolution())
            offsets.append(self.parts[axis_name].get_offset())

        for cs_axis in cs_axis_names:
            if cs_axis not in use:
                profile[cs_axis] = [0] * len(time_array)

        self.run_hook(self.BuildProfile, self.part_tasks, profile=profile,
                      use=use, resolutions=resolutions, offsets=offsets)

    def build_generator_profile(self, start=0):
        acceleration_time = self.calculate_acceleration_time()
        fraction = acceleration_time / self.exposure
        trajectory = {}
        time_array = []
        velocity_mode = []
        last_point = None

        for i in range(start, self.totalSteps.value):
            point = self.get_point(i)

            # Check that none of the external motors need moving
            if self.external_axis_has_moved(last_point, point):
                break

            # Check if we need to insert the lower bound point
            if last_point is None:
                lower_move_time = acceleration_time
            else:
                lower_move_time = self.need_lower_move_time(last_point, point)

            # Add lower bound time point
            if lower_move_time:
                if velocity_mode:
                    # set the previous point to not take this point into account
                    velocity_mode[-1] = PREV_TO_CURRENT
                velocity_mode.append(CURRENT_TO_NEXT)
                time_array.append(lower_move_time)

            # Add position and upper bound
            for x in range(2):
                time_array.append(self.exposure / 2.0)
                velocity_mode.append(PREV_TO_NEXT)

            # Add the axis positions
            for axis_name, cs_def in self.axis_mapping.items():
                positions = trajectory.setdefault(axis_name, [])
                # Add lower bound axis positions
                if lower_move_time:
                    positions.append(point.lower[axis_name])
                positions.append(point.positions[axis_name])
                positions.append(point.upper[axis_name])
            last_point = point

        # Add a tail off position
        for axis_name, tail_off in \
                self.run_up_positions(last_point, fraction).items():
            positions = trajectory[axis_name]
            positions.append(positions[-1] + tail_off)
        velocity_mode.append(ZERO)
        time_array.append(acceleration_time)

        self.build_profile(time_array, velocity_mode, trajectory)
        return i

    def need_lower_move_time(self, last_point, point):
        # First point needs to insert lower bound point
        lower_move_time = 0
        for axis_name, cs_def in self.axis_mapping.items():
            if last_point.upper[axis_name] != point.lower[axis_name]:
                # need to insert lower bound
                move_time = self.parts[axis_name].get_move_time(
                    last_point.upper[axis_name], point.lower[axis_name])
                lower_move_time = max(lower_move_time, move_time)
        return lower_move_time

    def external_axis_has_moved(self, last_point, point):
        for axis_name in self.generator.position_units:
            if axis_name not in self.axis_mapping:
                # Check it hasn't needed to move
                if point.positions[axis_name] != \
                        last_point.positions[axis_name]:
                    return True
        return False
