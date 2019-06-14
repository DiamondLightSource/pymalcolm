# Treat all division as float division even in python2
from __future__ import division

import numpy as np

from malcolm.core import Info


class MotorInfo(Info):
    def __init__(self,
                 cs_axis,  # type: str
                 cs_port,  # type: str
                 acceleration,   # type: float
                 resolution,  # type: float
                 offset,  # type: float
                 max_velocity,  # type: float
                 current_position,  # type: float
                 scannable,  # type: str
                 velocity_settle,  # type: float
                 units  # type: str
                 ):
        # type: (...) -> None
        self.cs_axis = cs_axis
        self.cs_port = cs_port
        self.acceleration = acceleration
        self.resolution = resolution
        self.offset = offset
        self.max_velocity = max_velocity
        self.current_position = current_position
        self.scannable = scannable
        self.velocity_settle = velocity_settle
        self.units = units

    def acceleration_time(self, v1, v2):
        # The time taken to ramp from v1 to pad_velocity
        ramp_time = abs(v2 - v1) / self.acceleration
        return ramp_time

    def ramp_distance(self, v1, v2, ramp_time=None):
        # The distance moved in the first part of the ramp
        if ramp_time is None:
            ramp_time = self.acceleration_time(v1, v2)
        ramp_distance = (v1 + v2) * ramp_time / 2
        return ramp_distance

    def _make_padded_ramp(self, v1, v2, pad_velocity, total_time):
        """Makes a ramp that looks like this:

        v1 \______ pad_velocity
           |      |\
           |      | \v2
         t1   tp   t2
        Such that whole section takes total_time
        """
        # The time taken to ramp from v1 to pad_velocity
        t1 = self.acceleration_time(v1, pad_velocity)
        # Then on to v2
        t2 = self.acceleration_time(pad_velocity, v2)
        # The distance during the pad
        tp = total_time - t1 - t2
        # Yield the points
        yield t1, pad_velocity
        yield tp, pad_velocity
        yield t2, v2

    def _calculate_hat_params(self, v1, v2, acceleration, distance):
        # Calculate how long to spend at max velocity
        if acceleration > 0:
            vm = self.max_velocity
        else:
            vm = -self.max_velocity
        t1 = self.acceleration_time(v1, vm)
        d1 = self.ramp_distance(v1, vm, t1)
        t2 = self.acceleration_time(vm, v2)
        d2 = self.ramp_distance(v1, vm, t1)
        dm = distance - d1 - d2
        tm = dm / vm
        return t1, tm, t2, vm

    def _make_hat(self, v1, v2, acceleration, distance, min_time):
        """Make a hat that looks like this:

            ______ vm
        v1 /|   | \
          d1| dm|d2\ v2
            |   |
          t1  tm t2

        Such that the area under the graph (d1+d2+d3) is distance and
        t1+t2+t3 >= min_time
        """
        if min_time > 0:
            # We are trying to meet time constraints
            # Solve quadratic to give vm
            b = v1 + v2 + min_time * acceleration
            c = distance * acceleration + (v1*v1 + v2*v2) / 2
            op = b*b - 4 * c
            if np.isclose(op, 0):
                # Might have a negative number as rounding error...
                op = 0
            elif op < 0:
                # Can't do this, set something massive to fail vm check...
                op = 10000000000

            def get_times(vm):
                t1 = (vm - v1) / acceleration
                t2 = (vm - v2) / acceleration
                tm = min_time - t1 - t2
                assert -self.max_velocity <= vm <= self.max_velocity
                assert t1 >= 0 and t2 >= 0 and tm >= 0
                return t1, tm, t2

            try:
                # Try negative root
                vm = (b - np.sqrt(op)) / 2
                t1, tm, t2 = get_times(vm)
            except AssertionError:
                try:
                    # Try positive root
                    vm = (b + np.sqrt(op)) / 2
                    t1, tm, t2 = get_times(vm)
                except AssertionError:
                    # If vm is out of range or any segment takes negative time,
                    # we can't do it in min_time, so act as if unconstrained
                    t1, tm, t2, vm = self._calculate_hat_params(
                        v1, v2, acceleration, distance)
        else:
            t1, tm, t2, vm = self._calculate_hat_params(
                v1, v2, acceleration, distance)

        # If middle segment needs to be negative time then we need to cap
        # vm and spend no time at vm
        if tm < 0:
            # Solve the quadratic to work out how long to spend accelerating
            vm = np.sqrt(
                (2 * acceleration * distance + v1 * v1 + v2 * v2) / 2)
            if acceleration < 0:
                vm = -vm
            t1 = self.acceleration_time(v1, vm)
            t2 = self.acceleration_time(vm, v2)
            tm = 0

        # Yield the result
        yield t1, vm
        yield tm, vm
        yield t2, v2

    def make_velocity_profile(self, v1, v2, distance, min_time):
        """Calculate PVT points that will perform the move within motor params

        Args:
            v1 (float): Starting velocity in EGUs/s
            v2 (float): Ending velocity in EGUs/s
            distance (float): Relative distance to travel in EGUs
            min_time (float): The minimum time the move should take

        Returns:
            tuple: (time_list, position_list) where time_list is a list of
                absolute time points in seconds, and position_list is the
                position in EGUs that the motor should be
        """
        # Take off the settle time and distance
        if min_time > 0:
            min_time -= self.velocity_settle
        distance -= self.velocity_settle * v2
        # The ramp time and distance of a continuous ramp from v1 to v2
        ramp_time = self.acceleration_time(v1, v2)
        ramp_distance = self.ramp_distance(v1, v2, ramp_time)
        remaining_distance = distance - ramp_distance
        # Check if we need to stretch in time
        if min_time > ramp_time:
            # Check how fast we would need to be going so that the total move
            # completes in min_time
            pad_velocity = remaining_distance / (min_time - ramp_time)
            if pad_velocity > max(v1, v2):
                # Can't just pad the ramp, make a hat pointing up
                it = self._make_hat(
                    v1, v2, self.acceleration, distance, min_time)
            elif pad_velocity < min(v1, v2):
                # Can't just pad the ramp, make a hat pointing down
                it = self._make_hat(
                    v1, v2, -self.acceleration, distance, min_time)
            else:
                # Make a padded ramp
                it = self._make_padded_ramp(v1, v2, pad_velocity, min_time)
        elif remaining_distance < 0:
            # Make a hat pointing down
            it = self._make_hat(v1, v2, -self.acceleration, distance, min_time)
        else:
            # Make a hat pointing up
            it = self._make_hat(v1, v2, self.acceleration, distance, min_time)
        # Create the time and velocity arrays
        time_array = [0.0]
        velocity_array = [v1]
        for t, v in it:
            assert t >= 0, "Got negative t %s" % t
            if t == 0:
                assert v == velocity_array[-1], \
                    "Can't move velocity in zero time"
                continue
            if v * velocity_array[-1] < 0:
                # Crossed zero, put in an explicit zero velocity
                fraction = velocity_array[-1] / (velocity_array[-1] - v)
                time_array.append(time_array[-1] + fraction * t)
                velocity_array.append(0)
                t -= fraction * t
            time_array.append(time_array[-1] + t)
            velocity_array.append(v)
        # Add on the settle time
        if self.velocity_settle > 0:
            time_array.append(time_array[-1] + self.velocity_settle)
            velocity_array.append(v2)
        return time_array, velocity_array

    def in_cts(self, position):
        # type: (float) -> int
        """Return the position (in EGUs) translated to counts"""
        cts = int(round((position - self.offset) / self.resolution))
        return cts

