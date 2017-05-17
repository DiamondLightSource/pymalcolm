Malcolm
=======

Malcolm is a middlelayer framework that implements high level configure/run
behaviour of control system components like those used in continuous scans.
This `repository`_ contains a Python implementation (pymalcolm) allowing the
creation of Malcolm servers and clients. There is also a `malcolmjs`_
JavaScript client and a `jmalcolm`_ Java client.

Malcolm was created as part of the `Mapping project`_ at `Diamond Light Source`_
in order to improve the performance of continuous scanning.

What can Malcolm do?
--------------------

Malcolm provides a layer on top of `EPICS`_
that wraps up groups of `PVs`_ and presents a higher level scanning interface to
`GDA`_ via `pvAccess`_.

.. digraph:: malcolm_dls_usage

    bgcolor=transparent
    node [fontname=Arial fontsize=10 shape=box style=filled fillcolor="#8BC4E9"]
    edge [fontname=Arial fontsize=10 arrowhead=vee]

    {rank=same;Detector EPICS "HDF File"}

    Malcolm [shape=doublecircle]

    GDA -> Malcolm [label="scan.configure()\nscan.run()"]
    Malcolm -> EPICS [label="caput\ncamonitor"]
    Detector -> EPICS [label="Frame data"]
    EPICS -> "HDF File" [label="Frame data"]
    EPICS -> "Motor Controller" [label="Motion trajectory"]


Malcolm was developed for continuous scanning and the diagram above shows
how Diamond uses it, but it can also be used in other ways:

* As a library that can be used in continuous scanning scripts without acting
  as a server
* As a webserver, exposing a web GUI for configuring the underlying hardware
  that communicates to Malcolm using `JSON`_ over `websockets`_
* As a distributed object system, using either `pvAccess`_ or `websockets`_ to
  communicate and synchronise objects between multiple Malcolm processes

How is the documentation structured?
------------------------------------

The documentation is structured into a series of `tutorials-doc` and some
general `reference-doc` documentation. End users and developers need different
documentation, so links for various categories of user are listed below:

Configuring Malcolm to work with your hardware
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Work through the `tutorials-doc` then look at the `malcolm.modules` API
documentation to see what arguments need to be passed to each object in the YAML
file.

Controlling Malcolm via comms protocols
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Read the `hello_tutorial`, then look at the `block_structure` and
`message_structure` sections. The `malcolm.modules.pva` module contains some
pvAccess specific documentation. The `RunnableStates` statemachine will also
be of interest.





.. _installation_guide:

Installation Guide
------------------

For now, in a Diamond environment just run::

    git clone https://github.com/dls-controls/pymalcolm

All optional modules are already installed and available






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

.. _repository:
    https://github.com/dls-controls/pymalcolm

.. _malcolmjs:
    https://github.com/dls-controls/malcolmjs

.. _jmalcolm:
    https://github.com/openGDA