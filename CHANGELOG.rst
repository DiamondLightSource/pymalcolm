Change Log
==========
All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning <http://semver.org/>`_ after 2-1.


`Unreleased`_
-------------

Nothing yet

`3-0a5`_ - 2018-10-17
---------------------

Changed:

- Web gui version (malcolmjs 1.3.1)

Fixed:

- Minor bug with loading non-existant attributes failing
- Some internal issues in p4p pvAccess support
- ProxyController refactor, moving some code to ClientComms


`3-0a4`_ - 2018-09-24
---------------------

Added:

- Web gui (malcolmjs 1.1.0)

Changed:

- PVAccess library from pvaPy to p4p. This means that monitor deltas and RPC
errors now work as expected

Fixed:

- PMAC trajectory pause waits for long enough to get GPIO signals
- MotorInfo.make_velocity_profile now works with small distances, zero
velocities, and a min_time. A floating point rounding error was previously
making it return less than min_time
- Make all areaDetectors wait on stop() for the acquire light to go out
- Updated DEFAULT_TIMEOUT to 10s
- Fixed pmac so that stretched pulses on a PROFILE_POINTS boundary work
- Added pollNow() for pmac GPIOs (requires pmac 2-1 or later)
- Enforce camelCaseFields and Alphanumeric + underscore + dash Part names
- Don't load child runnable block designs at init
- Error message when a Field is not writeable now shows current state
- Check generator units match axis units in pmac cs part
- Added "get" option to Put to allow current value to be returned
- out/inports are now source/sinkPorts
- Added widget:tree and widget:multilinetextupdate and removed widget:title
- rbv_suff is now rbv_suffix

`3-0a3`_ - 2018-07-25
---------------------

Fixed:

- PMAC move to start uses the right timeout (instead of fixed 5 seconds)
- SimultaneousAxes now works from axesToMove instead of generator axes

`3-0a2`_ - 2018-07-17
---------------------

Fixed:

- DLS specific require paths

`3-0a1`_ - 2018-07-16
---------------------

Changed:

- All yaml keys are snake_case rather than camelCase
- Default webserver port is now 8008
- axesToMove attribute has changed to simultaneousAxes
- Load save more explicit with initial_visibility on ChildParts
- Python classes now use `annotypes`_ for type introspection
- Hook decorators are replaced by a more explicit Part.register_hooked()
- DetectorDriverPart refactored to give a better interface


`2-3-1`_ - 2018-06-07
---------------------

Fixed:

- Graylog config for DLS logging to point to graylog2


`2-3`_ - 2018-05-31
-------------------

Added:

- event_timeout to future waiting functions

Fixed:

- HDF writer only waits up to 60s for new frames to tick before timing out
- Make hardware step scanning work


`2-2`_ - 2018-03-29
-------------------

Changed:

- Split arrayCounter into arrayCounter and arrayCounterReadback on ADCore ndarraybase_parts

Fixed:

- Made RunnableChildPart handle a resume on a child that was Armed not Paused
- Made VDS depend on h5py 2.7.1 and vds-gen 0.2
- Removed flaky sum datasets of VDS
- Fix a regression where Xmap would not report its DET and sum datasets

Added:

- dtacq support


`2-1`_ - 2017-08-30
-------------------
Changed:

- Major refactor, many breaking changes

`2-0a6`_ - 2016-10-03
---------------------
Changed:

- Attributes no longer serialize to NTAttribute, they now use NTScalar,
  NTScalarArray, NTTable or NTUnion

`2-0a5`_ - 2016-10-03
---------------------
Added:

- Support for PandABox

Fixed:

- Extra padding point in turnaround in PMACTrajectoryScan

`2-0a4`_ - 2016-09-20
---------------------
Added:

- PMAC trajectory scanning
- Pause, Abort and Rewind
- PVA: Get and Post for client

`2-0a3`_ - 2016-08-31
---------------------
Added:

- imalcolm client script

`2-0a2`_ - 2016-08-30
---------------------
Added:

- Ability to start comms from YAML
- PVAccess comms
- Dummy PMAC trajectory scan

2-0a1 - 2016-08-15
------------------
Added:

- Initial release with hello world and websocket comms

.. _Unreleased: https://github.com/dls-controls/pymalcolm/compare/3-0a5...HEAD
.. _3-0a5: https://github.com/dls-controls/pymalcolm/compare/3-0a4...3-0a5
.. _3-0a4: https://github.com/dls-controls/pymalcolm/compare/3-0a3...3-0a4
.. _3-0a3: https://github.com/dls-controls/pymalcolm/compare/3-0a2...3-0a3
.. _3-0a2: https://github.com/dls-controls/pymalcolm/compare/3-0a1...3-0a2
.. _3-0a1: https://github.com/dls-controls/pymalcolm/compare/2-3-1...3-0a1
.. _2-3-1: https://github.com/dls-controls/pymalcolm/compare/2-3...2-3-1
.. _2-3: https://github.com/dls-controls/pymalcolm/compare/2-2...2-3
.. _2-2: https://github.com/dls-controls/pymalcolm/compare/2-1...2-2
.. _2-1: https://github.com/dls-controls/pymalcolm/compare/2-0a6...2-1
.. _2-0a6: https://github.com/dls-controls/pymalcolm/compare/2-0a5...2-0a6
.. _2-0a5: https://github.com/dls-controls/pymalcolm/compare/2-0a4...2-0a5
.. _2-0a4: https://github.com/dls-controls/pymalcolm/compare/2-0a3...2-0a4
.. _2-0a3: https://github.com/dls-controls/pymalcolm/compare/2-0a2...2-0a3
.. _2-0a2: https://github.com/dls-controls/pymalcolm/compare/2-0a1...2-0a2

.. _annotypes: https://github.com/dls-controls/annotypes
