Change Log
==========
All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning <http://semver.org/>`_.

`Unreleased`_ - unreleased
--------------------------
Added:

- Nothing yet

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

.. _Unreleased: https://github.com/dls-controls/pymalcolm/compare/2-0a6...HEAD
.. _2-0a6: https://github.com/dls-controls/pymalcolm/compare/2-0a5...2-0a6
.. _2-0a5: https://github.com/dls-controls/pymalcolm/compare/2-0a4...2-0a5
.. _2-0a4: https://github.com/dls-controls/pymalcolm/compare/2-0a3...2-0a4
.. _2-0a3: https://github.com/dls-controls/pymalcolm/compare/2-0a2...2-0a3
.. _2-0a2: https://github.com/dls-controls/pymalcolm/compare/2-0a1...2-0a2

