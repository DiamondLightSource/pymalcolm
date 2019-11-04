# Treat all division as float division even in python2
from __future__ import division

from malcolm.core import Info
from .velocityprofile import VelocityProfile


class MotorInfo(Info):
    def __init__(self,
                 cs_axis,  # type: str
                 cs_port,  # type: str
                 acceleration,  # type: float
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

    def make_velocity_profile(
            self, v1, v2, distance, min_time, min_interval=0.002):
        """Calculate PVT points that will perform the move within motor params

        Args:
            v1 (float): Starting velocity in EGUs/s
            v2 (float): Ending velocity in EGUs/s
            distance (float): Relative distance to travel in EGUs
            min_time (float): The minimum time the move should take
            min_interval (float): Minimum time between profile points

        Returns:
            VelocityProfile: defining a list of times and velocities
        """

        # Create the time and velocity arrays
        p = VelocityProfile(
            v1, v2, distance, min_time, self.acceleration, self.max_velocity,
            self.velocity_settle, min_interval)
        p.get_profile()
        return p

    def in_cts(self, position):
        # type: (float) -> int
        """Return the position (in EGUs) translated to counts"""
        cts = int(round((position - self.offset) / self.resolution))
        return cts
