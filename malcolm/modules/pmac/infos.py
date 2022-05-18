from malcolm.core import Info

from .velocityprofile import VelocityProfile

import math


class PmacVariablesInfo(Info):
    """List variable values for variables required in kinematics

    Args:
        i_variables: i variable list
        p_variables: p variable list
        m_variables: m variable list
    """

    def __init__(self, i_variables: str, p_variables: str, m_variables: str) -> None:
        self.i_variables = i_variables
        self.p_variables = p_variables
        self.m_variables = m_variables
        self.all_variables = " ".join([i_variables, p_variables, m_variables])


class PmacCsKinematicsInfo(Info):
    """Coordinate sys kinematics programs and Q variable values

    Args:
        cs_port: the port name for this coordinate system
        q_variables: i variable list
        forward: forward kinematic code
        inverse: inverse kinematic code
    """

    def __init__(
        self, cs_port: str, q_variables: str, forward: str, inverse: str
    ) -> None:
        self.cs_port = cs_port
        self.q_variables = q_variables
        self.forward = forward
        self.inverse = inverse


class MotorInfo(Info):
    def __init__(
        self,
        cs_axis: str,
        cs_port: str,
        acceleration: float,
        resolution: float,
        offset: float,
        max_velocity: float,
        current_position: float,
        scannable: str,
        velocity_settle: float,
        units: str,
        user_high_limit: float,
        user_low_limit: float,
    ) -> None:
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
        self.user_high_limit = user_high_limit
        self.user_low_limit = user_low_limit

    def acceleration_time(self, v1, v2):
        # The time taken to ramp from v1 to pad_velocity
        ramp_time = abs(v2 - v1) / self.acceleration
        return ramp_time

    def ramp_distance(self, v1, v2, ramp_time=None, min_ramp_time=None):
        # The distance moved in the first part of the ramp
        if ramp_time is None:
            ramp_time = self.acceleration_time(v1, v2)
        if min_ramp_time is not None:
            ramp_time = max(ramp_time, min_ramp_time)
        ramp_distance = (v1 + v2) * ramp_time / 2
        return ramp_distance

    def make_velocity_profile(self, v1, v2, distance, min_time, min_interval=0.002):
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
            v1,
            v2,
            distance,
            min_time,
            self.acceleration,
            self.max_velocity,
            self.velocity_settle,
            min_interval,
        )
        p.get_profile()
        return p

    def in_cts(self, position: float) -> int:
        """Return the position (in EGUs) translated to counts"""
        cts = int(round((position - self.offset) / self.resolution))
        return cts

    def check_position_within_soft_limits(self, position: float) -> bool:
        """Check a position (in EGUs) against the soft limits and return True/False"""
        # Soft limits of 0.0, 0.0 on a motor record means we should ignore them
        if math.isclose(
            self.user_low_limit, 0.0, rel_tol=1e-12, abs_tol=1e-12
        ) and math.isclose(self.user_high_limit, 0.0, rel_tol=1e-12, abs_tol=1e-12):
            return True
        # Otherwise check the soft limits against the position
        elif position > self.user_high_limit or position < self.user_low_limit:
            return False
        else:
            return True
