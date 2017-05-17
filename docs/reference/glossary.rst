.. _glossary:

Glossary
========

Here are some commonly used Malcolm terms

Process
-------

A Malcolm `Process` hosts a number of `Controller`_ instances that can handle
requests meant for a particular `Block`_. First introduced in the
`hello_tutorial`.

Block
-----

A `Block` is the interface to a single object with Methods and Attributes.
Introduced in the `hello_tutorial`.

Controller
----------

A `Controller`

Part
----

A `Part`

Hardware Block
--------------

Lowest level of `Block`, providing an interface that directly exposes the
attributes that the hardware device provides. Introduced in the
`generator_tutorial`.

Device Block
------------

Middle level of `Block`, corresponding to a device like a Detector or a Motor
controller. They manage a number of Hardware blocks and expose a configure/run
interface. Introduced in the `generator_tutorial`.

Scan Block
----------

Top level of `Block`, corresponding to a combination of Devices making up a
scan.


