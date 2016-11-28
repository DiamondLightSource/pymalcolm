Hello World Tutorial
====================

If you have followed the installation guide, you will now have a checked out
copy of pymalcolm. Now would be a good time for a "Hello World" example.

Let's start with some terminology. A Malcolm application consists of a
:ref:`Process` which hosts a number of :ref:`Block` instances. Each Block has
a number of :ref:`Attribute` and :ref:`Method` instances that can be used to
interact with it. The Process may also contain :ref:`ServerComms` that allow
it to expose its Blocks to the outside world, and it may also contain
:ref:`ClientComms` that link it to another Malcolm Process and allow access
to its Blocks.

Launching a Malcolm Process
---------------------------

So how do we launch a Malcolm process? The simplest way is to use the
imalcolm application. It will be installed on the system as ``imalcolm``, but
you can use it from your checked out copy of pymalcolm by running
``./malcolm/imalcolm.py``. You also need to tell imalcolm what Blocks it
should instantiate and what Comms modules it should use by writing a `YAML`_
file.

Let's look at a ``./examples/DEMO-HELLO.yaml`` now:

.. literalinclude:: ../../examples/DEMO-HELLO.yaml

You will see 4 entries in the file. The first 3 entries are instantiating Blocks
that have already been defined. These Blocks each take a single argument, mri
(Malcolm Resource Identifier) which tells the Process how clients will
address that Block. The last entry tells the Process to start an HTTP server
on port 8080 and listen for websocket connections from another Malcolm
process or a web GUI.

.. highlight:: ipython

Let's run it now::

    [tmc43@pc0013 pymalcolm]$ ./malcolm/imalcolm.py examples/DEMO-HELLO.yaml
    Python 2.7.3 (default, Nov  9 2013, 21:59:00)
    Type "copyright", "credits" or "license" for more information.

    IPython 2.1.0 -- An enhanced Interactive Python.
    ?         -> Introduction and overview of IPython's features.
    %quickref -> Quick reference.
    help      -> Python's own help system.
    object?   -> Details about 'object', use 'object??' for extra details.


    Welcome to iMalcolm.

    self.process_block.blocks:
        ['DEMO-HELLO', 'HELLO', 'HELLO2', 'COUNTER']

    Try:
    hello = self.get_block("HELLO")
    print hello.greet("me")

    or

    gui(self.get_block("COUNTER"))

    or

    self.process_block.blocks


    In [1]:

We are presented with an `IPython`_ interactive console with the running
Process as ``self``. Let's try to get one of the Blocks we created from the
Process and call a Method on it::

    In [1]: hello = self.get_block("HELLO")

    In [2]: print hello.greet("me")
    Manufacturing greeting...
    Map({'greeting': 'Hello me'})

    In [3]:

So what happened there? Well we called a Method on a Block, which printed
"Manufacturing greeting..." to stdout, then returned a :ref:`Map` containing
the promised greeting. You can also specify an optional argument "sleep" to
make it sleep for a bit before returning the greeting::

    In [3]: print hello.greet("me again", sleep=2)
    Manufacturing greeting...
    Map({'greeting': 'Hello me again'})

    In [4]:

Connecting a second Malcolm Process
-----------------------------------

So how about accessing this object from outside the Process we just run about?
Well if we start a second imalcolm session we can tell it to connect to the
first session, get the HELLO block from the first Process, and run a Method
on it::

    [tmc43@pc0013 pymalcolm]$ ./malcolm/imalcolm.py -c ws://localhost:8080
    Python 2.7.3 (default, Nov  9 2013, 21:59:00)
    Type "copyright", "credits" or "license" for more information.

    IPython 2.1.0 -- An enhanced Interactive Python.
    ?         -> Introduction and overview of IPython's features.
    %quickref -> Quick reference.
    help      -> Python's own help system.
    object?   -> Details about 'object', use 'object??' for extra details.


    Welcome to iMalcolm.

    self.process_block.blocks:
        ['Process']

    Try:
    hello = self.get_block("HELLO")
    print hello.greet("me")

    or

    gui(self.get_block("COUNTER"))

    or

    self.process_block.blocks


    In [1]: hello = self.get_block("HELLO")

    In [2]: print hello.greet("me")
    Map({u'greeting': 'Hello me'})

    In [3]:

So how do we know it actually worked? Well if you look closely, you'll see
that the printed statement came out on the console of the first session
rather than the second session. This means that the Block in the first
session was doing the actual "work", while the Block in the second session
was just firing off a request and waiting for the response as shown in the
diagram below.

.. uml::

    !include docs/style.iuml

    frame "First Process" {
        frame HELLO {
            [Method greet] as H1.greet
        }

        frame COUNTER {
            [Attribute counter]
            [Method zero]
            [Method increment]
        }
    }

    frame "Second Process" {
        frame "HELLO " {
            [Method greet] as H2.greet
        }
    }

    H1.greet <.up.> H2.greet

You can quit those imalcolm sessions now by pressing CTRL-D or typing exit.

Defining a Block
----------------

We've found out how to create Blocks that have already been defined, so lets
have a look at how we define a Block. The Hello Block of the last example is
a good example, it is defined in the ``./malcolm/blocks/demo/Hello.yaml`` file:

.. highlight:: yaml

.. literalinclude:: ../../malcolm/blocks/demo/Hello.yaml

The first item in the YAML file is a :ref:`parameter`. This defines a parameter
that must be defined when instantiating the Block. It's value is then available
throughout the YAML file by using the ``$(<name>)`` syntax.

The second item is a :ref:`Controller`. This is responsible for creating the
Block and populating it with Methods and Attributes, and managing state
according to the :ref:`StateMachine` it implements.

The third item is a :ref:`Part`. A Controller can own many parts, and these
Parts can contribute Methods and Attributes, as well as being called at
specific times during Controller methods.

When we instantiate a Block, we are actually creating a Controller and Parts
which will then populate a Block object with Attributes and Methods which
will be kept up to date with whatever created it. In our Hello example, it
looks like this:

.. uml::

    !include docs/style.iuml

    object Process

    package "Data" <<Frame>> {
        object Block {
            mri: "HELLO"
        }
        object Method {
            name: "greet"
        }
        object Attribute {
            name: "state"
        }
    }

    package "Control" <<Frame>> {
        object DefaultController {
            state: Attribute
            block: Block
        }
        object HelloPart {
            greet: Method
        }
    }

    Process o-- Block
    Block o-- Attribute
    Block o-- Method
    Process *-- DefaultController
    DefaultController *-- Block
    DefaultController *-- Attribute
    DefaultController *-- HelloPart
    HelloPart *-- Method

The outside world only sees the Data side, but whenever a Method is called or
an Attribute set, something on the Control side is responsible for actioning
the request.

Defining a Part
---------------

We've seen that we don't write any code to define a Block, we compose it from
a Controller and Parts that give will contribute Methods and Attributes to it.
We will normally use one of the builtin Controllers, so the only place we
write code is when we define a Part. Let's take a look at our
``./malcolm/parts/demo/hellopart.py`` now:

.. highlight:: python

.. literalinclude:: ../../malcolm/parts/demo/hellopart.py

.. module:: malcolm.core

The class we define is called ``HelloPart`` and it subclasses from
:class:`Part`. It has a single method called ``greet`` that has some
`decorators`_ on it and contains the actual business logic.

Let's take a closer look at those decorators. The first,
:meth:`method_takes`, defines the arguments that the method will take and
hence the contents of the ``parameters`` :class:`Map`. The second,
:meth:`method_returns`, defines the arguments that the method will return.
The second argument ``return_map`` is an empty :class:`Map` that the method
can fill in and return.

Each of these decorators consumes its arguments in groups of 3:

- name (str): The name of the argument
- meta (:class:`VMeta`): A Meta object that will validate that argument
- :const:`OPTIONAL`/:const:`REQUIRED`/default: If REQUIRED then the argument
  must be specified, if OPTIONAL then it may be specified, otherwise the value
  is used as a default value for the argument

Inside the actual function, we print a message just so we can see what is
happening, then sleep for a bit to simulate doing some work, then place the
greeting into the return map and return it.

Conclusion
----------

This first tutorial has taken us through running up a Process with some
Blocks and shown us how those Blocks are specified by instantiating Parts and
placing them within a Controller. The HelloPart we have seen encapsulates the
functionality required to add a ``greet()`` function to a Block. It means
that we could now add "greeting" functionality to another Block just by
adding it to the instantiated parts. In the next tutorial we will read more
about this.

.. _YAML:
    https://en.wikipedia.org/wiki/YAML

.. _IPython:
    https://ipython.org

.. _decorators:
    https://realpython.com/blog/python/primer-on-python-decorators/
