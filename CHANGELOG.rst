Change Log
==========
All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning <http://semver.org/>`_ after 2-1.


`4-0`_ - 2019-07-05
-------------------

Added:

- PMAC Row Gate only trigger option for use with PandASeqTriggerPart
- PandA tutorial

Fixed:

- Now works with Python3.7
- ADCore HDF Writer now always writes at least some Attributes


`4-0b2`_ - 2019-06-20
---------------------

Changed:

- All PV arguments are now pv_prefix, not prefix

Added:

- PMAC Tutorial
- Live and Dead frame template for PandA


`4-0b1`_ - 2019-05-03
---------------------

Changed:

- CS and motors now show a link to parent PMAC, require pmac version 2-2
- Added Position Compare support for PandA via 2 SEQ blocks
- State machine. Added Finished state and Malcolm will now sit in Finished state
  after a scan
- CSMove changed to explicitly tell the motor controller how long it should take
  to do the move to start
- Changed seeking to not allow it to stop on a configured_step boundary
- Disable checking of scanpointgenerator units while GDA doesn't send the right
  ones
- PMAC should now be a ManagerController, with PmacChildPart in the scan
- PandA now specifies datasets in a Bits and Positions table
- Web GUI now takes last run parameters from server for methods
- All identifiers in YAML must now be in snake_case

Added:

- Make use of FlushNow in ADCore, which flushes data and attributes after every
  second during run() or when commanded through the record on HDF Writer. Files
  are kept open until next reset()/abort()

Fixed:

- caactionpart now waits for good status, prevents timeout errors when doing
  caputs

Added:

- ADEiger support
- Improved ADAndor support with knowledge of frame transfer mode

Fixed:

- Race condition on making async logging at imalcolm startup

`3-5`_ - 2019-06-17
-------------------

Changed:

- Removed local file logging
- Add pymalcolm version tag to Block meta
- Support no axis scans in PMAC. Requires pmac xxxx
- Do as many scanpointgenerator dimensions as possible to support acquire scans

`3-4-1`_ - 2019-05-08
---------------------

Fixed:

- no_save now saves everything apart from what is passed. Previously it was
  updating a set that was common to all ChildPart subclasses
- pmactrajectorypart no longer checks CS numbers on validate in case they are
  different to what is saved


`3-4`_ - 2019-03-28
-------------------

Added:

- ADOdin VDS and nexus file generation
- HDF Attributes control of NDAttributes written
- Windows detector file path support
- added precision and units to number attributes

Fixed:

- Update to malcolmjs 1.6.2 to fix cryptic errors


`3-3`_ - 2019-02-19
-------------------

Added:

- Precision and units in a display_t for NumberMeta
- Number of frames per chunk in HDF writer Block saved
- Merlin support
- Waveform Table support with plot widget in malcolmjs

Fixed:

- Disconnected PVs now keep their value, rather than zeroing it
- Update malcolmjs to 1.6.1
- Subtle bug with turnaround trajectories at high accelerations
- Made explicit the attributes that are managed by ChildPart and shouldn't save
- save() now calls sync so file is flushed to disk (for PandA)


`3-2`_ - 2019-01-21
-------------------

Added:

- ADOdin support for start/stop (not rewind or VDS yet)
- Configurable poll period of PandA

Fixed:

- Performance tweaks for PandA web control, which makes time_t unordered dict
- Better error message for wrong cs_port in a trajectory scan


`3-0`_ - 2019-01-04
-------------------

Changed:

- areaDetectors now set acquirePeriod = exposure + readout_time
- Andor calculates readout_time from the reported driver values

Added:

- soft_trigger_modes to DetectorDriverPart to calculate is_hardware_triggered

Fixed:

- Look at operstart rather than flags to see if link is down for WebSockets
- BrickPart can now take initial_visibility again (broken in 3-0b2)
- Add git username and email settings at save for git versions that support it


`3-0b2`_ - 2018-12-05
---------------------

Added:

- PYMALCOLM_STACK_SIZE environment variable setting coroutine stack size
- Default is still 0 (coroutines share stack)
- DetectorDriverPart now also writes acqurirePeriod if writing exposure

Fixed:

- ADAndor now uses imageMode=Multiple not Fixed
- ADAndor now uses standard DetectorDriverPart


`3-0b1`_ - 2018-12-04
---------------------

Fixed:

- Trajectory scan back to level driven pulses as 24V GPIO has soft falling edges
- Update malcolmjs to 1.5.1

`3-0a9`_ - 2018-12-03
---------------------

Fixed:

- Websocket only validates for interfaces that are up
- Motor records have a number of records read only if they don't need writing


`3-0a8`_ - 2018-11-30
---------------------

Changed:

- Websocket server now blocks write access from outside subnet

Fixed:

- PandA now reports correct datasets to the HDF writer to link
- ADAndor does exposure time in a more standard way

`3-0a7`_ - 2018-11-27
---------------------

Changed:

- cothread is now a required dependency

Fixed:

- Updated first 3 tutorials to match Malcolm3 changes
- Bug on saving a new design after loading design=""

Updated:

- Web gui version (malcolmjs 1.5)


`3-0a6`_ - 2018-11-05
---------------------

Fixed:

- p4p imalcolm packaging and >= handling
- Some documentation updates

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

.. _Unreleased: https://github.com/dls-controls/pymalcolm/compare/4-0...HEAD
.. _4-0: https://github.com/dls-controls/pymalcolm/compare/4-0b2..4-0
.. _4-0b2: https://github.com/dls-controls/pymalcolm/compare/4-0b1..4-0b2
.. _4-0b1: https://github.com/dls-controls/pymalcolm/compare/3-4-1..4-0b1
.. _3-5: https://github.com/dls-controls/pymalcolm/compare/3-4-1...3-5
.. _3-4-1: https://github.com/dls-controls/pymalcolm/compare/3-4...3-4-1
.. _3-4: https://github.com/dls-controls/pymalcolm/compare/3-3...3-4
.. _3-3: https://github.com/dls-controls/pymalcolm/compare/3-2...3-3
.. _3-2: https://github.com/dls-controls/pymalcolm/compare/3-0...3-2
.. _3-0: https://github.com/dls-controls/pymalcolm/compare/3-0b2...3-0
.. _3-0b2: https://github.com/dls-controls/pymalcolm/compare/3-0b1...3-0b2
.. _3-0b1: https://github.com/dls-controls/pymalcolm/compare/3-0a9...3-0b1
.. _3-0a9: https://github.com/dls-controls/pymalcolm/compare/3-0a8...3-0a9
.. _3-0a8: https://github.com/dls-controls/pymalcolm/compare/3-0a7...3-0a8
.. _3-0a7: https://github.com/dls-controls/pymalcolm/compare/3-0a6...3-0a7
.. _3-0a6: https://github.com/dls-controls/pymalcolm/compare/3-0a5...3-0a6
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
