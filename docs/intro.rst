Malcolm is a middlelayer service that allows high level configure/run control
of control system components generally involved in continuous scans. This
module contains a python implementation allowing the creation of Malcolm
servers and clients.

What can Malcolm do?
--------------------

Malcolm was created as part of the `Mapping project`_ at `Diamond Light Source`_
to make continuous scanning faster. It provides a layer on top of `EPICS`_
that wraps up groups of `PVs`_ and presents a higher level scanning interface to
`GDA`_ via `pvAccess`_.

.. uml::

    !include docs/style.iuml

    [GDA] -down-> [Malcolm] : scan.configure()\nscan.run()
    [Malcolm] -down-> [EPICS] : caput\ncamonitor
    [Detector] -right-> [EPICS] : frame data
    [EPICS] -right-> [HDF File] : frame data
    [EPICS] -down-> [Motor Controller]: motion trajectory

Malcolm was created to do continuous scanning, and the diagram above shows
how Diamond uses it, but it can also be used in other ways:

* As a library that can be used in continuous scanning scripts without acting
  as a server
* As a webserver, exposing a web GUI for configuring the underlying hardware
  that communicates to Malcolm using `JSON`_ over `websockets`_
* As a distributed object system, using either `pvAccess`_ or `websockets`_ to
  communicate and synchronise objects between multiple Malcolm processes

How is the documentation structured?
------------------------------------

This documentation is broken into two sections:

* :ref:`user-docs` - How to run a Malcolm server that talks to supported
  hardware and write Malcolm support for a new piece of hardware
* :ref:`developer-docs` - Protocol specifications and API documentation

.. _Mapping project:
    https://indico.esss.lu.se/event/357/session/8/contribution/63

.. _EPICS:
    http://www.aps.anl.gov/epics/

.. _PVs:
    https://ics-web.sns.ornl.gov/kasemir/train_2006/1_3_CA_Overview.pdf

.. _GDA:
    http://www.opengda.org/

.. _pvAccess:
    http://epics-pvdata.sourceforge.net/arch.html#Network

.. _websockets:
    https://en.wikipedia.org/wiki/WebSocket

.. _Diamond Light Source:
    http://www.diamond.ac.uk

.. _JSON:
    http://www.json.org/


