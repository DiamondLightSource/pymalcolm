from math import fabs, sqrt

import numpy as np

HAT = 1
INVERSE_HAT = 2
RAMP = 3
INVERSE_RAMP = 4

R_TOL = 1e-10


class VelocityProfile:
    r"""
    Generate a velocity profile that starts at v1 and finishes at v2 in time t
    and travels distance d for a motor with acceleration a and maximum velocity
    v_max.

    There are 4 possible shapes: hat, inverted hat, rising or falling ramp.

    All profiles start at v1, accelerate to vm and remain there for tm and then
    accelerate to v2. Thus all profiles have 4 points, or 3 points if tm is
    zero.

    hat profile:
            ______ vm
        v1 /|   | \
          d1| dm|d2\ v2
            |   |
          t1 tm  t2

    falling ramp profile:
        v1\
           \______ vm
           |      |\
           |      | \v2
         t1   tp   t2

    Properties:
        v1: start velocity
        v2: final velocity
        d: distance to travel
        t_total: desired minimum time between v1 and v2 (to include settle time)
        a: motor acceleration (always used for the slopes in the result)
        v_max: maximum speed of the motor

        t1: the time interval from v1 to vm
        tm: the time interval at vm
        t2: the time interval from vm to v2
        vm: the velocity in the middle portion of the hat or ramp
        t_out: the adjust time if t is too short to achieve d
        interval: minimum interval between any two points in a profile

        d_trough: minimum distance possible between v1,v2 in tv2
        d_peak: maximum distance possible between v1,v2 in t
        v_trough: minimum velocity possible between v1,v2 with acceleration a
        v_peak: maximum velocity possible between v1,v2  with acceleration a
    """

    def __init__(
        self,
        v1: float,
        v2: float,
        d: float,
        t_total: float,
        a: float,
        v_max: float,
        settle_time: float = 0,
        interval: float = 0,
    ) -> None:
        """
        Initialize the properties that define the desired profile

        Args:
        v1: start velocity
        v2: final velocity
        d: distance to travel
        tv2: time between v1 and v2
        a: motor acceleration (always used for the slopes in the result)
        v_max: motor maximum velocity
        settle_time: period to stay at final velocity to allow motor to settle
        """
        self.v1 = v1
        self.v2 = v2
        self.d = d - v2 * settle_time
        self.tv2 = t_total - settle_time
        self.t_total = t_total
        self.a = a
        self.v_max = v_max
        self.settle_time = settle_time
        self.interval = interval

        # these attributes set by calling get_profile()
        self.t1 = self.tm = self.t2 = self.vm = 0
        self.d_trough = self.d_peak = self.v_trough = self.v_peak = 0
        self.t_peak = self.t_trough = 0

        # once we have quantized it is important to freeze the time intervals
        self.quantized = False

        assert not np.isclose(a, 0), "zero acceleration is illegal"
        assert fabs(v1) <= v_max and fabs(v2) <= v_max, "v1, v2 must be <= v_max"
        assert v_max > 0 and a > 0, "v_max, acceleration must be > 0"

    def check_range(self):
        r"""
        Calculate the positive and negative velocity maxima attainable between
        v1 and v2 within time tv2. This allows the calculations of the maximum
        and minimum distance attainable. It deliberately ignores v_max so that
        we get the parallelogram below.

               v_peak
                /\
              /   \
            /      \v2
        v1/        /
          \      /
           \   /
            \/
          v_trough
         |  |   |  |
        0  tt  tp  tv2  - times relative to v1 time
        """

        # first calculate tp by seeing where the acceleration
        # lines (-ve and +ve) from v1 and v2 cross each other
        # the acceleration lines for v1 and v2 are
        # v = v1 + at
        # v = v2 + a(tv2-t)
        # solving simultaneous equations for t
        # t = (at - v1 + v2) / 2 a
        self.t_peak = (self.a * self.tv2 - self.v1 + self.v2) / (2 * self.a)
        self.t_trough = self.tv2 - self.t_peak

        # calculate the velocities at the peak and trough
        self.v_peak = self.v1 + self.a * self.t_peak
        self.v_trough = self.v1 - self.a * self.t_trough

        # calculate the maximum and minimum distances attainable by hitting the
        # above maxima. i.e. sum 2 trapezoids described by v1, v_peak, v2
        # and the x axis
        self.d_peak = (self.v1 + self.v_peak) * self.t_peak / 2 + (
            self.v2 + self.v_peak
        ) * (self.tv2 - self.t_peak) / 2
        self.d_trough = (self.v1 + self.v_trough) * self.t_trough / 2 + (
            self.v2 + self.v_trough
        ) * (self.tv2 - self.t_trough) / 2
        # this helps with the domain checks in calculate_vm()
        if np.isclose(self.d, self.d_trough, rtol=R_TOL):
            self.d_trough = self.d
        if np.isclose(self.d, self.d_peak, rtol=R_TOL):
            self.d_peak = self.d

    def calculate_times(self, vm=None):
        vm = self.vm if vm is None else vm

        # derive the times from vm
        self.t1 = fabs(vm - self.v1) / self.a
        self.t2 = fabs(self.v2 - vm) / self.a
        self.tm = self.tv2 - self.t1 - self.t2

    def calculate_distance(self, vm=None):
        """
        calculate the area under the velocity/time graph.

        The math simply sums the area of two trapezoids and a rectangle.
        Note that this works even when 1 or more of the shapes straddles zero
        (or one of t1, tm, t2 is zero)

        Args:
            vm: override the internal value of vm for this calculation
        """
        vm = self.vm if vm is None else vm

        # make sure the peak and troughs are set correctly
        self.check_range()

        # pull vm in if it is outside reachable range
        vm = self.v_peak if vm > self.v_peak else vm
        vm = self.v_trough if vm < self.v_trough else vm

        # set the times for t1, tp, t2
        if not self.quantized:
            self.calculate_times(vm=vm)

        d1 = (self.v1 + vm) * self.t1 / 2
        d2 = vm * self.tm
        d3 = (self.v2 + vm) * self.t2 / 2
        d_out = d1 + d2 + d3 + self.v2 * self.settle_time
        return d_out

    def stretch_time(self):
        """
        Determine if it is possible to reach distance d in the time t.
        If not calculate a new minimum t.

        STEP 1
        Stretch time without accounting for v_max. This expands the
        parallelogram defined in the check_range() docstring.

        The area representing d is defined by the top half of the
        parallelogram bisected by the x axis. This can be
        described as two trapezoids z1, z2
        with height1, height2, width as follows:-
          v1, v_peak, t_peak     for z1
          v2, v_peak, tv2-t_peak   for z2
        combining nd simplifying the two functions for area of trapezoid:
          d = (t * (vp+v2)-tp * (v2-v1)) / 2
        substitute in the peak functions from check_range for vp, tp and
        solve for t:
          tv2 = (sqrt(2) * sqrt(2*a*d3+v1**2+v2**2)-v1-v2) / a

        STEP 2
        Now apply v_max and recalculate the d. If it needs stretching
        further then we are only expanding the rectangle described by
           height = v_max
           width = increase in tv2 from the one calculated above
        To reduce range use trough instead of peak to derive similar functions.
        """

        # STEP 1
        if self.d > self.calculate_distance(vm=100000):
            self.tv2 = (
                sqrt(2) * sqrt(2 * self.a * self.d + self.v1 ** 2 + self.v2 ** 2)
                - self.v1
                - self.v2
            ) / self.a
        elif self.d < self.calculate_distance(vm=-100000):
            self.tv2 = (
                -(
                    -sqrt(2) * sqrt(2 * self.a * -self.d + self.v1 ** 2 + self.v2 ** 2)
                    - self.v1
                    - self.v2
                )
                / self.a
            )
        # STEP2
        dc = self.calculate_distance(vm=self.v_max)
        if self.d > dc:
            self.tv2 += (self.d - dc) / self.v_max
        else:
            dc = self.calculate_distance(vm=-self.v_max)
            if self.d < dc:
                self.tv2 += (dc - self.d) / self.v_max

        self.t_total = self.tv2 + self.settle_time

    def calculate_vm(self):
        r"""
        to ensure this function will succeed, call stretch_time() first.

        Once we have adjusted tv2 to ensure that d is attainable we can now
        calculate the value for vm. This is in effect the inverse of
        calc_distance() however inverting the function does not work since
        the parameters can all be of any sign (giles spent several days proving
        this).
            v_peak____________
                /\
              /   \           zone 3
            /______\v2________
        v1/________/__________zone 2
          \      /
           \   /              zone 1
            \/________________
          v_trough
         |  |   |  |
        0  tt  tp  tv2  - times relative to v1 time

        calculate the max distance travelled for each 'Zone' in the diagram
        above. These are zones for ranges of values for Vm and represent
        areas with different rates of change of distance relative to
        change in Vm
        The area calculations are as follows:-
          ramps = 2 triangles representing acceleration to 0 from v1, v2.
                    The area under ramps is the distance that is travelled
                    for any value of vm. Note that either or both can have
                    negative area.
          zone 1 = inverted triangle, tip at v_trough, hypotenuse the
                    lesser of v2, v1.
                    When sliced by vm the lower half is triangle representing
                    the distance in addition to ramps
          zone 2 = parallelogram between V2 and V1 with ends described by a
                    the intersection with the acceleration lines.
                    When sliced by vm the lower half parallelogram represents
                    the distance in addition to z1 + ramps
          zone 3 = triangle, tip at v_peak, hypotenuse at the greater
                    of v1, v2.
                    When sliced by vm the lower half is a trapezoid representing
                    the distance in addition to z2 + z1 +ramps

        The Calculations for the area under vm in each zone are
        as follows:

        Zone 1 triangle:
        more_d =  Height * Width / 2
        more_d = (vm - v_trough) * (2 * (vm - v_trough) / a) / 2
        invert for vm

        Zone 2 parallelogram:
        more_d = Height * Width
        more_d = (vm-v_high) * zones_width
        invert for vm

        Zone 3 trapezoid:
        it is much neater to subtract the area of top triangle from z3 area
        more_d = d_z1 - Height * Width / 2
        more_d = d_z1 - (v_peak-vm) * (2*v_peak-vm/a) /2
        invert for vm (but cope with singularity)
        """

        # v_low is the lower of v1 v2 and v_high the higher of the two
        if self.v1 > self.v2:
            v_low, v_high = self.v2, self.v1
        else:
            v_low, v_high = self.v1, self.v2
        zones_width = self.tv2 - (v_high - v_low) / self.a
        z1_height = v_low - self.v_trough
        z3_height = self.v_peak - v_high
        z2_height = self.v_peak - self.v_trough - z1_height - z3_height

        d_z1 = z1_height * zones_width / 2
        d_z2 = z2_height * zones_width
        d_z3 = z3_height * zones_width / 2

        # find out which zone d is in and then determine how far into that
        # zone vm needs to extend to get the correct d. For each calculation
        # more_d is the difference between distance described by the lower
        # zones and the target distance
        assert (
            self.d_trough <= self.d <= self.d_peak
        ), "cannot achieve distance d, time stretch required"
        if np.isclose(self.v_peak, v_high, rtol=R_TOL):
            # the profile is a straight line
            self.vm = (v_high + v_low) / 2
        elif self.d < self.d_trough + d_z1:
            # its in zone 1
            more_d = self.d - self.d_trough
            self.vm = self.v_trough + sqrt(more_d) * sqrt(self.a)
        elif self.d < self.d_trough + d_z1 + d_z2:
            # its zone 2
            more_d = self.d - self.d_trough - d_z1
            self.vm = v_low + more_d / zones_width
        elif self.d <= self.d_peak:
            # its zone 3
            more_d = self.d - self.d_trough - d_z1 - d_z2
            if np.isclose(d_z3 - more_d, 0):
                self.vm = self.v_peak
            else:
                self.vm = self.v_peak - sqrt(self.a * (d_z3 - more_d))
        else:
            assert False, "should not reach here"

        assert (
            np.isclose(self.v_peak, self.vm)
            or np.isclose(self.v_trough, self.vm)
            or self.v_trough <= self.vm <= self.v_peak
        ), "velocity out of range, check the math"
        assert (
            np.isclose(self.v_max, self.vm) or self.vm <= self.v_max
        ), "velocity exceeds maximum, check the math"

    def get_profile(self):
        """
        determine what profile can achieve d in tv2 between v1 and v2
        with a and v_max. Stretch tv2 if necessary.

        The results are stored in the following properties which describe the
        profile to take:
        t1, tm, t2, vm, tv2 (tv2 is an input property but may be stretched)

        :Returns Array(float), Array(float): absolute time and velocity arrays
        """
        min_time = fabs(self.v1 - self.v2) / self.a
        self.tv2 = max(self.tv2, min_time)
        self.t_total = self.tv2 + self.settle_time

        t = self.tv2
        self.stretch_time()
        if self.tv2 != t:
            self.check_range()
        self.calculate_vm()
        self.calculate_times()

        # validate the results
        assert (
            np.isclose(self.d_peak, self.d)
            or np.isclose(self.d_trough, self.d)
            or self.d_trough <= self.d <= self.d_peak
        ), "distance is outside of allowed trough and peak, check the math"

    def check_quantize(self):
        """
        Check if this profile has any times that are not on a 'size' second
        boundary. Such profiles require quantization for them to be safely
        combined with other axis profiles (which will also require
        quantization). Otherwise the combined profile may contain very small
        time intervals that pmac PVT cannot achieve.

        Returns bool: true if this profile requires quantization:
        """
        times = np.array([self.t1, self.tm, self.t2])
        # don't quantize profiles that are shorter than interval
        if self.tv2 > self.interval > 0:
            decimals = (times / self.interval) % 1
            result = not np.isclose(decimals, np.round(decimals)).all()
            return result

    def quantize(self):
        """
        ensure that all time points are exactly on 'interval' second boundaries
        do this by:
            add 1 milliseconds to t1, tm, t2 and round down
            adjust vm downwards so that d is correct
        When reducing vm, keep t1, tm the same but adjust the
        acceleration downwards.

        the function for vm was derived by taking the sum of the area of
        two trapezoids and a rectangle described by v1, vm, v2, t1, tm, t2
        then solving for vm
        https://www.wolframalpha.com/input/?i=solve+d%3D%28v1%2Bv0%29%2F2
        +t1+%2B+v0+t0+%2B+%28v2%2Bv0%29%2F2+t2+for+v0

        :Returns Array(float), Array(float): absolute time and velocity arrays
        """

        # First round the times to remove any tiny fractions that would waste
        # an extra millisecond when doing math.ceil()
        #
        # Next increase total time by 2 'interval' and round up to the nearest
        # even number of 'interval' - this is then deterministic for all axes,
        # and includes at least enough stretch to accommodate up to 'interval'
        # of stretch in each slope time.
        #
        # For a flat hat, round up the two slope times and the flat time is
        # the remainder.
        #
        # For a pointy hat add 1 to t1 and round up, then t2 is the remainder.
        #
        # This approach preserves symmetry but at the same time ensures that
        # total time is increased deterministically plus acceleration and
        # vm are decreased (thus not exceeding max acceleration, velocity)
        self.tv2 = np.round(self.tv2, decimals=14)
        self.t1 = np.round(self.t1, decimals=14)
        self.t2 = np.round(self.t2, decimals=14)
        self.tv2 = np.ceil((self.tv2 + self.interval * 2) / (self.interval * 2)) * (
            self.interval * 2
        )
        if self.tm == 0:
            # pointy hat
            self.t1 = np.ceil(self.t1 / self.interval + 1) * self.interval
            self.t2 = self.tv2 - self.t1
        else:
            # flat topped hat
            self.t1 = np.ceil(self.t1 / self.interval) * self.interval
            self.t2 = np.ceil(self.t2 / self.interval) * self.interval
            self.tm = self.tv2 - self.t1 - self.t2

        # recalculate the middle velocity (peak velocity for a pointy hat)
        # using the new times
        i1 = -2 * self.d + self.t1 * self.v1 + self.t2 * self.v2
        i2 = 2 * self.tm + self.t1 + self.t2
        self.vm = -i1 / i2

        self.t_total = self.tv2 + self.settle_time
        self.quantized = True

    def make_arrays(self):
        """
        Convert the time and velocity properties to arrays for consumption
        by pmac/util.py

        :Returns Array(float), Array(float): absolute time, velocity arrays
        """
        # return ABSOLUTE time and velocity arrays to describe the profile
        if self.tv2 <= self.interval:
            # for profiles that are shorter than the min interval
            # we only return the start and end with no mid points
            time_array = [0.0, self.tv2]
            velocity_array = [self.v1, self.v2]
        elif self.d == 0 and self.v1 == 0 and self.v2 == 0:
            time_array = [0.0, self.tv2]
            velocity_array = [0, 0]
        else:
            time_array = [0.0, self.t1, self.tv2]
            velocity_array = [self.v1, self.vm, self.v2]
            if self.tm > 0:
                time_array.insert(2, self.t1 + self.tm)
                velocity_array.insert(2, self.vm)
        if self.settle_time > 0:
            time_array.append(time_array[-1] + self.settle_time)
            velocity_array.append(self.v2)
        time_array = np.around(time_array, 10)

        # some of the math results in tiny fractions which affect some of the
        # tests - round to 12 decimals
        velocity_array = np.around(velocity_array, 12)
        time_array = np.around(time_array, 12)
        return list(time_array), list(velocity_array)
