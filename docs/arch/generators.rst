Scan Point Generator
====================

There are a number of pieces of information about each point in a scan that are
needed by parts of Malcolm and GDA:

- The demand positions of a number of actuators representing where they should
  be at the  mid-point of a detector frame. This is needed for step scans and
  continuous scans.
- The demand positions of those actuators at the upper and lower bounds (start
  and end) or that detector frame. This is needed for continuous scans only so
  that each detector frame is taken while the actuators were moving at a
  constant velocity
- The index in the data file that the frame should be stored. For grid based
  scan (like a snake scan), these will have the same dimensions as the demand
  positions. For non grid based scans (like a spiral scan), these will have
  less dimensions because the datapoints do not fit onto a regular grid.

The size of each index dimension, the name of each index dimension, and units
for each actuator are also provided for the scan.

A separate project called `Scan Point Generator`_ has been setup to create
these definitions.

These generators will be used by the Position Labeller to stamp the positions
in the HDF file, the HDF writer for the dimensions of the file, and the Motor
Trajectory for the positions to move the motors to.

They are specified by passing a table of generators to the configure() of the
top level scan:

    ======= =============== ======= ======= ======= ======= ======
    Name    Type            Arg1    Arg2    Arg3    Arg4    Arg5
    ======= =============== ======= ======= ======= ======= ======
    xs      LineGenerator   x       mm      0       0.1     5
    ys      LineGenerator   y       mm      1       0.1     4
    gen     NestedGenerator ys      xs
    ======= =============== ======= ======= ======= ======= ======

The last generator in the table will be the one that is used in the scan.

.. _Scan Point Generator:
    http://scanpointgenerator.readthedocs.org/en/latest/writing.html
