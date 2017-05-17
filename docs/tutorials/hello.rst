.. _hello_tutorial:

Hello World Tutorial
====================

If you have followed the `installation_guide` you will have a checked out a
copy of pymalcolm which includes some example code.
  
So now would be a good time for a "Hello World" tutorial.

Let's start with some terminology. A Malcolm application consists of a `Process`
which hosts a number of `Block` instances. Each Block has a number of
`Attribute` and `Method` instances that can be used to interact with it. The
Process may also contain `ServerComms` that allow it to expose its Blocks to the
outside world, and it may also contain `ClientComms` that link it to another
Malcolm Process and allow access to its Blocks.

Launching a Malcolm Process
---------------------------

So how do we launch a Malcolm process? 

The simplest way is to use the imalcolm application. It will be installed on the
system as ``imalcolm``, but you can use it from your checked out copy of
pymalcolm by running ``./malcolm/imalcolm.py``. You also need to tell imalcolm
what Blocks it should instantiate and what Comms modules it should use by
writing a `YAML`_ file.

Let's look at ``./examples/DEMO-HELLO.yaml`` now:

.. literalinclude:: ../../examples/DEMO-HELLO.yaml
    :language: yaml

You will see 4 entries in the file. The first 3 entries are instantiating Blocks
that have already been defined. These Blocks each take a single mri (Malcolm
Resource Identifier) argument which tells the Process how clients will address
that Block. The last entry creates a ServerComms Block which starts an HTTP
server on port 8080 and listen for websocket connections from another Malcolm
process or a web GUI.

.. highlight:: ipython

Let's run it now::

    [tmc43@pc0013 pymalcolm]$ ./malcolm/imalcolm.py examples/DEMO-HELLO.yaml
    Loading...
    Python 2.7.3 (default, Nov  9 2013, 21:59:00)
    Type "copyright", "credits" or "license" for more information.

    IPython 2.1.0 -- An enhanced Interactive Python.
    ?         -> Introduction and overview of IPython's features.
    %quickref -> Quick reference.
    help      -> Python's own help system.
    object?   -> Details about 'object', use 'object??' for extra details.


    Welcome to iMalcolm.

    self.mri_list:
        ['localhost:8080']

    Try:
    hello = self.block_view("HELLO")
    print hello.greet("me")

    or

    gui(self.block_view("COUNTER"))

    or

    self.make_proxy("localhost:8080", "HELLO")
    print self.block_view("HELLO").greet("me")


    In [1]:

We are presented with an `IPython`_ interactive console with the running
Process as ``self``. Let's try to get one of the Blocks we created from the
Process and call a Method on it::

    In [1]: hello = self.block_view("HELLO")

    In [2]: print hello.greet("me")
    Manufacturing greeting...
    Map({'greeting': 'Hello me'})

    In [3]:

So what happened there? 

Well we called a Method on a Block, which printed
"Manufacturing greeting..." to stdout, then returned a `Map` containing
the promised greeting. You can also specify an optional argument "sleep" to
make it sleep for a bit before returning the greeting::

    In [3]: print hello.greet("me again", sleep=2)
    Manufacturing greeting...
    Map({'greeting': 'Hello me again'})

    In [4]:

Connecting a second Malcolm Process
-----------------------------------

So how about accessing this object from outside the Process we just ran?

Well if we start a second imalcolm session we can tell it to connect to the
first session, get the HELLO block from the first Process, and run a Method
on it::

    [tmc43@pc0013 pymalcolm]$ ./malcolm/imalcolm.py -c ws://localhost:8080
    Loading...
    Python 2.7.3 (default, Nov  9 2013, 21:59:00)
    Type "copyright", "credits" or "license" for more information.

    IPython 2.1.0 -- An enhanced Interactive Python.
    ?         -> Introduction and overview of IPython's features.
    %quickref -> Quick reference.
    help      -> Python's own help system.
    object?   -> Details about 'object', use 'object??' for extra details.


    Welcome to iMalcolm.

    self.mri_list:
        ['localhost:8080']

    Try:
    hello = self.block_view("HELLO")
    print hello.greet("me")

    or

    gui(self.block_view("COUNTER"))

    or

    self.make_proxy("localhost:8080", "HELLO")
    print self.block_view("HELLO").greet("me")


    In [1]: self.make_proxy("localhost:8080", "HELLO")

    In [2]: print self.block_view("HELLO").greet("me")
    Map({'greeting': 'Hello me'})

    In [3]:

So how do we know it actually worked? 

Well if you look closely, you'll see
that the printed statement ``Manufacturing greeting...`` came out on the console
of the first session rather than the second session (you can get your prompt
back on the first session by pressing return). This means that the Block in the
first session was doing the actual "work", while the Block in the second session
was just firing off a request and waiting for the response as shown in the
diagram below.

.. digraph:: distributed_object_usage

    bgcolor=transparent
    node [fontname=Arial fontsize=10 shape=box style=filled fillcolor="#8BC4E9"]
    graph [fontname=Arial fontsize=11 fillcolor="#DDDDDD"]
    edge [fontname=Arial fontsize=10 arrowhead=vee]

    subgraph cluster_p2 {
        label="Second Process"
        subgraph cluster_h2 {
            label="Hello Block"
            style=filled
            g2 [label="greet()"]
            e2 [label="error()"]
        }
    }

    subgraph cluster_p1 {
        label="First Process"
        subgraph cluster_c1 {
            label="Counter Block"
            style=filled
            counter "zero()" "increment()"
        }
        subgraph cluster_h1 {
            label="Hello Block"
            style=filled
            g1 [label="greet()"]
            e1 [label="error()"]
        }
    }

    g2 -> g1 [style=dashed label="Post(name='me')"]
    g1 -> g2 [style=dashed label="Return(greeting='Hello me')"]

You can quit those imalcolm sessions now by pressing CTRL-D or typing exit.

Defining a Block
----------------

We have already seen that a `Block` is made up of `Method` and `Attribute`
instances, but how do we define one? Well, although Methods and Attributes make
a good interface to the outside world, they aren't the right size unit to divide
our Block into re-usable chunks of code. What we actually need is something to
co-ordinate our Block and provide a framework for the logic we will write, and
plugins that can extend and customize this logic. The object that play a
co-ordinating role is called a `Controller` and each plugin is called a `Part`.
This is how they fit together:

.. digraph:: controllers_and_parts

    bgcolor=transparent
    node [fontname=Arial fontsize=10 shape=Mrecord style=filled fillcolor="#8BC4E9"]
    graph [fontname=Arial fontsize=11]
    edge [fontname=Arial fontsize=10 arrowhead=none]

    Process

    subgraph cluster_control {
        label="Control"
        labelloc="b"
        Controller -> Parts
    }

    subgraph cluster_view {
        label="View"
        labelloc="b"
        Block -> Methods
        Block -> Attributes
    }

    {rank=same;Controller Block}

    Process -> Controller
    Controller -> Block [arrowhead=vee dir=from style=dashed label=produces]

The `Controller` is responsible for making a Block View on request that we can
interact with. It populates it with Methods and Attributes that it has created
as well as those created by `Part` instances attached to it. Parts are also
called at specific times during Controller Methods to allow them to contribute
logic.

Lets take a look at how the Hello Block of the last example is created. It is
defined in the ``./malcolm/modules/demo/blocks/hello_block.yaml`` file:

.. literalinclude:: ../../malcolm/modules/demo/blocks/hello_block.yaml
    :language: yaml

The first item in the YAML file is a `parameter`. This defines a parameter that
must be defined when instantiating the Block. It's value is then available
throughout the YAML file by using the ``$(<name>)`` syntax.

The second item is a `BasicController` that just acts as a container for Parts.
It only contributes a ``health`` Attribute to the Block.

The third item is a `HelloPart`. It contributes the ``greet()`` and ``error()``
Methods to the Block.

Here's a diagram showing who created those Methods and Attributes:

.. digraph:: hello_controllers_and_parts

    bgcolor=transparent
    node [fontname=Arial fontsize=10 shape=box style=filled fillcolor="#8BC4E9"]
    graph [fontname=Arial fontsize=11]
    edge [fontname=Arial fontsize=10 arrowhead=none]

    controller [shape=Mrecord label="{BasicController|mri: 'HELLO'}"]
    hello [shape=Mrecord label="{HelloPart|name: 'hello'}"]

    subgraph cluster_control {
        label="Control"
        labelloc="b"
        controller -> hello
    }

    block [shape=Mrecord label="{Block|mri: 'HELLO'}"]
    greet [shape=Mrecord label="{Method|name: 'greet'}"]
    error [shape=Mrecord label="{Method|name: 'error'}"]
    health [shape=Mrecord label="{Attribute|name: 'health'}"]

    subgraph cluster_view {
        label="View"
        labelloc="b"
        block -> greet
        block -> error
        block -> health
    }

    {rank=same;controller block}

    controller -> health [style=dashed]
    hello -> greet [style=dashed]
    hello -> error [style=dashed]
    controller -> block [arrowhead=vee dir=from style=dashed label=produces]

The outside world only sees the View side, but whenever a Method is called or
an Attribute set, something on the Control side is responsible for actioning
the request.

Defining a Part
---------------

We've seen that we don't write any code to define a Block, we compose it from a
Controller and the Parts that contribute Methods and Attributes to it. We will
normally use one of the builtin Controllers, so the only place we write code is
when we define a Part. Let's take a look at our
``./malcolm/modules/demo/parts/hellopart.py`` now:

.. literalinclude:: ../../malcolm/modules/demo/parts/hellopart.py
    :language: python

.. py:currentmodule:: malcolm.core

The class we define is called ``HelloPart`` and it subclasses from
`Part`. It has a single method called ``greet`` that has some
`decorators`_ on it and contains the actual business logic. In Python,
decorators can be stacked many deep and can modify the function or class they
are attached to.

Let's take a closer look at those decorators. 

1. `method_takes` defines the arguments that the ``greet`` method will take and
   hence the contents of the  ``parameters`` argument. Malcolm will take any input arguments,
   validate them, and create a `Map` instance with the `method_takes` arguments

2. `method_returns` defines the values that the method will return. Malcolm will create
   an empty `Map` configured to validate the items specified in `method_returns`
   and pass it as ``return_map``, the final argument to ``greet``.

Both of these decorators consumes their arguments in groups of 3:

- name (str): The name of the argument
- meta (`VMeta`): A Meta object that will validate that argument
- `OPTIONAL`/`REQUIRED`/default_value: If REQUIRED then the argument
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
about adding functionality using Parts.

.. _YAML:
    https://en.wikipedia.org/wiki/YAML

.. _IPython:
    https://ipython.org

.. _decorators:
    https://realpython.com/blog/python/primer-on-python-decorators/
