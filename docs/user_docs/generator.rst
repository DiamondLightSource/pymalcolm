Generator Tutorial
==================

You should already know how to create a :ref:`Part` that attaches
:ref:`Attribute` and :ref:`Method` instances to a :ref:`Block`.
The Blocks we have made in previous tutorials are quite simple and low level,
and might correspond to the interface provided by EPICS devices, a collection
of Attributes that we can set and simple Methods we can call that cause the
device to operate in a particular way. What is missing is the logic of "do
this, then that, then these 3 things at the same time". To do this, we will
create a higher level Block that will control a number of child Blocks to
synchronise them and use them for a particular application.

These higher level Blocks have two main methods:

- configure(params): Take a set of parameters, and configure all child Blocks
  according to these parameters. This operation should include as much as
  possible of the setup of the device, without actually starting a scan.
- run(): When all devices taking part in the scan have configured themselves,
  this method with start the scan going. It supervises the actions of the
  scan, providing status monitoring and any periodic actions that need to
  happen.

The application we have chosen for this tutorial is a ScanTicker. It will take
the specification for a scan, then use a number of Counter blocks that we saw in
the last tutorial, setting them to the demand positions of the axes in the
scan. This will look a little like a Motor Controller performing a continuous
scan.

Let's take a look at the Process definition ``./examples/DEMO-TICKER.yaml``:

.. literalinclude:: ../../examples/DEMO-TICKER.yaml
    :language: yaml

That's not very exciting, we just load a single Ticker Block and a Comms
object. Let's look at ``./malcolm/blocks/demo/Ticker.yaml`` to see what one
of those does:

.. literalinclude:: ../../malcolm/blocks/demo/Ticker.yaml
    :language: yaml

.. currentmodule:: malcolm.controllers

We instantiate two Counter blocks, and instantiate two ScanTickerParts that
will connect to them. We then use a :class:`RunnableController` to construct
our Block. This is probably better viewed as a diagram:

.. uml::

    !include docs/style.iuml

    package "TICKER" <<Frame>> {
        object Block1 {
            mri: "TICKER"
        }
        object Method1 {
            name: "configure"
        }
        object Method2 {
            name: "run"
        }
        object RunnableController
        object ScanTickerPart1 {
            child: COUNTERX
        }
        object ScanTickerPart2 {
            child: COUNTERY
        }
        Block1 o-- Method1
        Block1 o-- Method2
        RunnableController *-left- Block1
        RunnableController *-- Method1
        RunnableController *-- Method2
        RunnableController *-- ScanTickerPart1
        RunnableController *-- ScanTickerPart2
    }

    package "COUNTERX" <<Frame>> {
        object Block2 {
            mri: "COUNTERX"
        }
        object Attribute1 {
            name: "counter"
        }
        object DefaultController1
        object CounterPart1 {
            counter: Attribute1
        }
        Block2 o-- Attribute1
        DefaultController1 *-left- Block2
        DefaultController1 *-- CounterPart1
        CounterPart1 *-left- Attribute1
    }

    package "COUNTERY" <<Frame>> {
        object Block3 {
            mri: "COUNTERY"
        }
        object Attribute2 {
            name: "counter"
        }
        object DefaultController2
        object CounterPart2 {
            counter: Attribute2
        }
        Block3 o-- Attribute2
        DefaultController2 *-left- Block3
        DefaultController2 *-- CounterPart2
        CounterPart2 *-left- Attribute2
    }

    ScanTickerPart1 o-- Block2
    ScanTickerPart2 o-- Block3

The :class:`RunnableController` contributes the ``configure`` and ``run``
Methods in a similar way to previous examples, but the two ScanTickerParts do
not contribute any Attributes or Methods to the Block. Instead, these register
functions with :class:`~malcolm.core.Hook` instances on the Controller to
make their child Block behave in a particular way during the correct phase of
:meth:`~RunnableController.configure` or :meth:`~RunnableController.run`.

Specifying Scan Points
----------------------

If this ScanTicker Block is going to simulate running a scan, we better learn
how to specify a scan. There are a number of pieces of information about each
point in a scan that are needed by parts of Malcolm:

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
- The duration of the frame. This is needed for continuous scans and is the
  time taken to get from the lower to the upper bound

The size of each index dimension and units for each actuator are also
needed for file writing.

Rather than passing all this information in one large structure, a separate
project called `Scan Point Generator`_ has been setup to create parameterized
generators which work together to generate multi-dimensional scan paths. We
will make our ScanTicker Block understand these generators.


Hooking into configure() and run()
----------------------------------

We mentioned earlier that a Part can register functions to run the correct
phase of Methods provided by the Controller. Lets take a look at
``parts.demo.scantickerpart.py`` to see how this works:

.. literalinclude:: ../../malcolm/parts/demo/scantickerpart.py
    :language: python

.. py:currentmodule:: malcolm


You'll notice rather a lot of decorators on those functions. The
``@RunnableController.*`` lines register a function with a :class:`~core.Hook`.
A :ref:`Controller` defines a a number of Hooks that define what methods
of a :ref:`Part` will be run during a particular :ref:`Method`. For
example, we are hooking our ``configure()`` method to the
:attr:`~controllers.RunnableController.Configure` Hook. Let's take a
look at its documentation:

.. py:currentmodule:: malcolm.controllers

.. autoattribute:: RunnableController.Configure
    :noindex:





.. _Scan Point Generator:
    http://scanpointgenerator.readthedocs.org/en/latest/writing.html
