Generator Tutorial
==================

You should already know how to create a `Part` that attaches
`Attribute` and `Method` instances to a `Block`.
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

We instantiate two Counter blocks, and instantiate two ScanTickerParts that
will connect to them. We then use a `RunnableController` to construct
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

The `RunnableController` contributes the ``configure`` and ``run``
Methods in a similar way to previous examples, but the two ScanTickerParts do
not contribute any Attributes or Methods to the Block. Instead, these register
functions with `Hook` instances on the Controller to
make their child Block behave in a particular way during the correct phase of
`RunnableController.configure` or `RunnableController.run`.

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
phase of Methods provided by the Controller. Lets take a look at the first
part of ``parts.demo.scantickerpart.py`` to see how this works:

.. literalinclude:: ../../malcolm/parts/demo/scantickerpart.py
    :language: python
    :end-before: @RunnableController.Run

You'll notice some more decorators on those functions. The
``@RunnableController.Configure`` line registers a function with a `Hook`.
A `Controller` defines a a number of Hooks that define what methods
of a `Part` will be run during a particular `Method`. For
example, we are hooking our ``configure()`` method to the
`Configure` Hook. Let's take a look at its documentation:

.. py:currentmodule:: malcolm.controllers

.. autoattribute:: RunnableController.Configure
    :noindex:

What happens in practice is that when ``TICKER.configure()`` is called, all the
functions hooked to `Configure` will be called concurrently. They will each
be passed the five arguments listed in the documentation above. Our ScanTicker
``configure()`` method simply stores the relevant information so that the
``run()`` method can operate on it. Lets look at that next:

.. literalinclude:: ../../malcolm/parts/demo/scantickerpart.py
    :language: python
    :start-after: self.generator = None

This is hooked to the `Run` Hook. Let's take a look at its documentation:

.. autoattribute:: RunnableController.Run
    :noindex:

Walking through the code we can see that we are iterating through each of the
step indexes that we need to produce, getting a `scanpointgenerator.Point`
object for each one.
We then pick out the position of the current axis, and use the `Task` to put
the value to the ``counter`` value. It is important that we use ``task`` to
do this rather than doing ``self.child.counter = value`` because this is
interruptable. The `Task` helper can also do asynchronous puts, and puts to
multiple attributes at the same time.

After we have done the put, we work out how long we need to wait until the
next position is to be produced, then do an interruptable sleep. Finally we
call ``update_completed_steps`` with the step number (note that steps are
1-indexed so that 0 can signify no steps complete) and self, the object that
is producing the update.

.. highlight:: ipython

Let's run up the example and give it a go::

    [tmc43@diamtr317 pymalcolm]$ ./malcolm/imalcolm.py examples/DEMO-TICKER.yaml
    INFO:COUNTERX.reset:I'm not writeable
    INFO:COUNTERX:Exception while handling ordereddict([('typeid', 'malcolm:core/Post:1.0'), ('id', 0), ('endpoint', ['COUNTERX', 'reset']), ('parameters', None)])
    INFO:COUNTERY.reset:I'm not writeable
    INFO:COUNTERY:Exception while handling ordereddict([('typeid', 'malcolm:core/Post:1.0'), ('id', 0), ('endpoint', ['COUNTERY', 'reset']), ('parameters', None)])
    Python 2.7.3 (default, Nov  9 2013, 21:59:00)
    Type "copyright", "credits" or "license" for more information.

    IPython 2.1.0 -- An enhanced Interactive Python.
    ?         -> Introduction and overview of IPython's features.
    %quickref -> Quick reference.
    help      -> Python's own help system.
    object?   -> Details about 'object', use 'object??' for extra details.


    Welcome to iMalcolm.

    self.process_block.blocks:
        ['DEMO-TICKER', 'COUNTERX', 'COUNTERY', 'TICKER']

    Try:
    hello = self.get_block("HELLO")
    print hello.greet("me")

    or

    gui(self.get_block("COUNTER"))

    or

    self.process_block.blocks


    In [1]: from scanpointgenerator import LineGenerator, CompoundGenerator, FixedDurationMutator

    In [2]: ticker = self.get_block("TICKER")

    In [3]: yline = LineGenerator("y", "mm", 0., 1., 6)

    In [4]: xline = LineGenerator("x", "mm", 0., 1., 5, alternate_direction=True)

    In [5]: duration = FixedDurationMutator(0.5)

    In [6]: generator = CompoundGenerator([yline, xline], [], [duration])

    In [7]: ticker.configure(generator, ["x", "y"])

    In [8]: gui(ticker)

    In [9]: gui(self.get_block("COUNTERX"))

    In [10]: gui(self.get_block("COUNTERY"))


What we have done here is set up a scan that is 6 rows in y and 5 columns in x.
The x value will snake forwards and backwards, and the y value will increase
at the end of each x row. We have told it that each scan point should last for
0.5 seconds, which should give us enough time to see the ticks. If you now
click the run button on the TICKER window, you should now see a scan performed:

.. image:: ticker_1.png

From here you can try pausing, resuming and seeking within the scan. What is
happening under the hood is that our hooked ``configure()`` method is being
called during ``pause()``, ``configure()`` and ``seek()``, but we want it to
do the same thing each time so can use the same method. The ``run()`` command
is likewise hooked to both ``run()`` and ``resume()`` as it makes no
difference in our example. In a real example, there may be some device state
that would mean different things need to be run in these two hooks.

Conclusion
==========

This tutorial has given us an understanding of how scans are specified
in Malcolm, how child Blocks are controlled from parent Blocks, and how Parts
can register code to run at different phases of a Controller.

.. _Scan Point Generator:
    http://scanpointgenerator.readthedocs.org/en/latest/writing.html
