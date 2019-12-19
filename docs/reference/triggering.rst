.. _trajectory_scan_triggering:

Trajectory Scan Triggering
==========================

PMAC-based Triggering
---------------------

This is intended as a description of how trigger signals are used and generated
for a trajectory scan. It uses the DLS trajectory scan motion program for PMAC
and Power PMAC. An example of this in use can be found in the `pmac_tutorial`.

There are 3 GPIO signals used to provide triggering information for detectors.
All of these signals are considered to trigger on a rising edge. They are all
fed into a PandA which uses them to determine when to average motor positions
and when to trigger the detector(s). The signals are :

* Live signal: Indicates the start of a frame
* Dead signal: Indicates the start of a period where no frames are acquired
* Centre signal: Indicates that we are in the middle of the current frame

When a series of frames are taken back to back, the live signal triggers for
the start of each. The dead signal triggers at the end of the last frame.

When Malcolm uploads lists of PVT points to the trajectory scan motion program
it also uploads a User Subroutine to be called as each point is reached. The
first 8 of these represent all combinations of the 3 GPIO Signals as follows:

====== ====== ====== ======
User   GPIO 0 GPIO 1 GPIO 2
Sub    Live   Dead   Centre
====== ====== ====== ======
1      0      0      1
2      0      1      0
3      0      1      1
4      1      0      0
5      1      0      1
6      1      1      0
7      1      1      1
8      0      0      0
====== ====== ====== ======

The diagram below shows an example of a snake scan with 6 data points and the
corresponding trigger signals.

The graph at the bottom shows the states of the GPIO lines as the PVT scan
progresses through its points.

Note that the acquisition time is shorter than the live time. This trigger
signal for the detector is controlled by the PandA. At present it pulses after
the transition of the live signal, delayed by half the readout time. The end of
acquisition is determined by the settings on the detector and this would be set
to live time - readout time.

Some of the PVT points are provided by Malcolm for convenience, and are used to:
    1. Provide a centre frame signal, and
    2. Tightly control turnaround path so that motors do not exceed their
       limits. The turnaround PVT points are added for locations where the
       acceleration changes.

.. image:: triggering_0.png


Using the PandA for Triggering
------------------------------

The current PMAC devices at Diamond are limited to a maximum of 300Hz for the
above signals. If this is exceeded, other processing on the PMAC will not have
enough time to complete. It is, however, quite straightforward to set-up and
use.

In order to use a higher detector trigger rate, the PandA can be used to
generate the majority of the above signals itself. Using a single trigger signal
to indicate the start of each row, it will trigger the detectors as well as
position capture. The `panda_tutorial` uses this method for triggering.


The start-of-row signal can be generated in two ways:

1. PandA position compare
    * This requires straight through mapped axes (no kinematics)
    * This requires that turnarounds are more than 100ms, to provide enough
      time for processing
    * This has the benefit of making rows line up in snake scans if there is
      significant following error on axes
2. PMAC row triggers
    * This can be used with kinematics
    * The row triggers have a maximum rate of 300Hz
