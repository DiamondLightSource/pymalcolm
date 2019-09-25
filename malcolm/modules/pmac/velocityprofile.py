import matplotlib.pyplot as plt
import numpy as np
import math

HAT = 1
INVERSE_HAT = 2
RAMP = 3
INVERSE_RAMP = 4


class VelocityProfile:
    """
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
        t: time between v1 and v2
        a: motor acceleration (always used for the slopes in the result)

        t1: the time interval from v1 to vm
        tm: the time interval at vm
        t2: the time interval from vm to v2
        vm: the velocity in the middle portion of the hat or ramp
        t_out: the adjust time if t is too short to achieve d

        d_trough: minimum distance possible between v1,v2 in t
        d_peak: maximum distance possible between v1,v2 in t
        v_trough: minimum velocity possible between v1,v2 with acceleration a
        v_peak: maximum velocity possible between v1,v2  with acceleration a
    """

    def __init__(
            self, v1: float, v2: float, d: float, t: float, a: float,
            v_max: float
    ) -> (float, float, float, float, float, float):
        """
        Initialize the properties that define the desired profile

        Args:
        v1: start velocity
        v2: final velocity
        d: distance to travel
        t: time between v1 and v2
        a: motor acceleration (always used for the slopes in the result)
        v_max: motor maximum velocity
        """
        self.v1 = v1
        self.v2 = v2
        self.d = d
        self.t = t
        self.a = a
        self.v_max = v_max

        # these attributes set by calling get_profile()
        self.t1 = self.tm = self.t2 = self.vm = None
        self.d_trough = self.d_peak = self.v_trough = self.v_peak = None

        assert not np.isclose(a, 0), "zero acceleration is illegal"
        assert not np.isclose(t, 0), "zero time is illegal"

    def calc_distance(self):
        """
        calculate the area under the velocity/time graph.

        The math simply sums the area of two trapezoids and a rectangle.
        Note that this works even when 1 or more of the shapes straddles zero
        (or one of the t values is zero)
        """

        d1 = (self.v1 + self.vm) * self.t1 / 2
        d2 = self.vm * self.tm
        d3 = (self.v2 + self.vm) * self.t2 / 2
        d_out = d1 + d2 + d3
        return d_out

    def check_range(self):
        """
        Calculate the positive and negative velocity maxima attainable between
        v1 and v2 within time t. This allows the calculations of the maximum and
        minimum distance attainable.

        If d cannot be attained then stretch t so that it can.

        It also defines a parallelogram which is essential to the this classes'
        approach to determining the profile

               v_peak     ____
                /\
              /   \            zone 3
            /      \v2    ____
        v1/        /      ____ zone 2
          \      /
           \   /               zone 1
            \/            ____
          v_trough

         |  |   |  |    (times relative to v1 time)
        0  tt  tp  t
        """

        # first calculate tp by seeing where the acceleration
        # lines (-ve and +ve) from v1 and v2 cross each other
        t_peak = (self.a * self.t - self.v1 + self.v2) / (2 * self.a)
        t_trough = self.t - t_peak

        # calculate the velocities at the peak and trough
        self.v_peak = self.v1 + self.a * t_peak
        self.v_trough = self.v1 - self.a * t_trough

        # calculate the maximum and minimum distances attainable by hitting the
        # above maxima. i.e. sum 2 trapezoids described by v1, v_peak, v2
        # and the x axis
        self.d_peak = (self.v1 + self.v_peak) * t_peak / 2 + \
                      (self.v2 + self.v_peak) * (self.t - t_peak) / 2
        self.d_trough = (self.v1 + self.v_trough) * t_trough / 2 + \
                        (self.v2 + self.v_trough) * (self.t - t_trough) / 2

        # if we can't achieve distance d then stretch t accordingly until the
        # peak or trough just achieves d (note that further stretch may be
        # required once we apply v_max see -- TODO)

        # TODO TODO ALSO TRY TO HANDLE VMAX HERE!! for a neat solution

    def calculate_vm(self):
        """
        Once we have adjusted t_out to ensure that d is attainable we can now
        calculate the value for vm. This is in effect the inverse of
        calc_distance() however inverting the function does not work since
        the parameters can all be of any sign (giles spent several days proving
        this).

        DO THE ASCII ART BUT GET IT WORKING FIRST!

        calculate the max distance travelled for each 'Zone' see ascii art above
        these are zones for Vm and represent areas with different rates of
        change
        of distance relative to change in Vm
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
        """

        # v_low is the lower of v1 v2 and v_high the higher of the two
        if self.v1 > self.v2:
            v_low, v_high = self.v2, self.v1
        else:
            v_low, v_high = self.v1, self.v2
        zones_width = self.t - (v_high - v_low) / self.a
        z1_height = v_low - self.v_trough
        z3_height = self.v_peak - v_high
        z2_height = self.v_peak - self.v_trough - z1_height - z3_height

        d_ramps = (self.v1 ** 2 / self.a + self.v2 ** 2 / self.a) / 2
        d_z1 = z1_height * zones_width / 2
        d_z2 = z2_height * zones_width
        d_z3 = z3_height * zones_width / 2
        d_total = d_z1 + d_z2 + d_z3
        assert np.isclose(d_total, self.d_peak - self.d_trough), \
                "Distance calculation is incorrect, check the math"

        # find out which zone d is in and then determine how far into that
        # zone vm needs to extend to get the correct d. For each calculation
        # more_d is the difference between distance described by the lower
        # zones and the target distance
        if self.d < d_z1 - d_ramps:
            # its in zone 1
            more_d = self.d - self.d_trough
            self.vm = self.v_trough + math.sqrt(more_d) * math.sqrt(self.a)
        elif self.d < d_z1 + d_z2 - d_ramps:
            # its zone 2
            more_d = self.d - self.d_trough - d_z1
            self.vm = v_low + more_d / zones_width
        else:
            # its zone 3
            more_d = self.d - self.d_trough - d_z1 - d_z2
            self.vm = self.v_peak - math.sqrt(
                self.a * (d_z3 - more_d))
        """
        The above Calculations for the area under vm in each zone are
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
        invert for vm
        """

        print("zone distances {}, {}, {}, ramp {}, total {}".format(
            d_z1, d_z2, d_z3, d_ramps, d_total))
        print("velocity peak {:03.3f}, trough {:3.3f}".format(
            self.v_peak, self.v_trough))
        print("distance peak {:03.3f}, trough {:3.3f}".format(
            self.d_peak, self.d_trough))
        print("vm {}".format(self.vm))

    def stretch_time(self):
        """
        Determine if it is possible to reach distance d in the time t
        if not provide the minimum value for t in self.t_out
        """

    def get_profile(self):
        """
        determine what profile can achieve d in t between v1 and v2
        with a and v_max.
        """
        self.check_range()
        self.calculate_vm()
        if self.stretch_time():
            self.calculate_vm()
        if not self.d_trough <= self.d <= self.d_peak:
            return None

        # derive the remaining results from vm
        self.t1 = math.fabs(self.vm - self.v1) / self.a
        self.t2 = math.fabs(self.v2 - self.vm) / self.a
        self.tm = self.t - self.t1 - self.t2

        # return a convenience tuple (for tests only)
        return self.v1, self.vm, self.v2, self.t1, self.tm, self.t2