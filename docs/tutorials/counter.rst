.. _counter_tutorial:

Counter Tutorial
================

.. py:currentmodule:: malcolm.core

You should already know how to run up a Malcolm `process_` with some `Blocks
<block_>` that are each composed of `controller_` with `Parts <part_>`, and have
seen a Part that exposes a `method_`. Now we will look at a Part that exposes an
`attribute_` as well.

Let's take the example of a Counter. It contains:

- a writeable `attribute_` called ``counter`` which will keep the current
  counter value.
- a `method_` zero() which will set ``counter = 0``.
- a `method_` increment() which will set ``counter = counter + 1``.

The block definition in ``./malcolm/modules/demo/blocks/counter_block.yaml``
looks very similar to the hello_block example in the previous tutorial:

.. literalinclude:: ../../malcolm/modules/demo/blocks/counter_block.yaml
    :language: yaml

It creates the Methods and Attributes you would expect:

.. digraph:: counter_controllers_and_parts

    bgcolor=transparent
    node [fontname=Arial fontsize=10 shape=box style=filled fillcolor="#8BC4E9"]
    graph [fontname=Arial fontsize=11]
    edge [fontname=Arial fontsize=10 arrowhead=none]

    controller [shape=Mrecord label="{BasicController|mri: 'COUNTER'}"]
    cpart [shape=Mrecord label="{CounterPart|name: 'counter'}"]

    subgraph cluster_control {
        label="Control"
        labelloc="b"
        controller -> cpart
    }

    block [shape=Mrecord label="{Block|mri: 'COUNTER'}"]
    zero [shape=Mrecord label="{Method|name: 'zero'}"]
    increment [shape=Mrecord label="{Method|name: 'increment'}"]
    counter [shape=Mrecord label="{Attribute|name: 'counter'}"]
    health [shape=Mrecord label="{Attribute|name: 'health'}"]

    subgraph cluster_view {
        label="View"
        labelloc="b"
        block -> zero
        block -> increment
        block -> counter
        block -> health
    }

    {rank=same;controller block}

    controller -> health [style=dashed]
    cpart -> zero [style=dashed]
    cpart -> increment [style=dashed]
    cpart -> counter [style=dashed]
    controller -> block [arrowhead=vee dir=from style=dashed label=produces]

Creating Attributes in a Part
-----------------------------

Let's take a look at the definition of `CounterPart` in
``./malcolm/modules/demo/parts/counterpart.py`` now:

.. literalinclude:: ../../malcolm/modules/demo/parts/counterpart.py
    :language: python

Again, we start by subclassing `Part`, but this time we do some extra work in
the ``__init__`` method. Whenever we override ``__init__`` it is important to
call the ``__init__`` that we have just overridden, and that is what the
`super` call does. This is a Python construct that lets us reliably call methods
of our superclass that we have just overridden, even if multiple inheritance is
used. If someone instantiates CounterPart, then
``super(CounterPart, self).__init__`` will return the ``__init__`` function of
the `Part`, bound so that ``self`` does not need to be passed into it.

.. note::
    It's not necessary to understand what `super` does, but it is necessary to
    use it when you need to call the method you have just overridden, otherwise
    your class may not behave correctly if subclassed and multiple inheritance
    is used.

We also add a type comment to the ``__init__`` method that tells anyone using
the Part what parameters should be passed to the initializer. In this case, we
don't actually add any parameters, just the ``name`` parameter that has been
defined by `Part`, so we can reuse the ``APartName`` Anno object to avoid
having to duplicate the type and description of this parameter.

Finally for ``__init__`` we create an `AttributeModel`. To make the
AttributeModel we first need to make a meta object. In our example we want a
``float64`` `NumberMeta` as we want to demonstrate floating point numbers. If
our counter was an integer we could choose ``int32`` or ``int64``. The actual
AttributeModel is returned by the :meth:`~VMeta.create_attribute_model` method
of this meta so that the correct type of AttributeModel can be chosen by the
particular type of Meta object we specify. We specify a number of
`tags_reference` on the Meta object that gives some hints about how this
Attribute will be used. In this case, we specify a `config_tag` to say that
this field is a configuration variable that will be marked for load/save, and
a `Widget` tag that tells a GUI which widget to use to display this Attribute.


The ``setup`` function looks very similar to the one in the previous tutorial,
but this time we also register our `AttributeModel` so it appears in the parent
`block_`. We do this by calling :meth:`~PartRegistrar.add_attribute_model` with
3 arguments:

- ``"counter"``: the name of the Attribute within the Block
- ``self.counter``: the AttributeModel instance
- ``self.counter.set_value``: the function that will be called when someone
  tries to "Put" to the Attribute. If one isn't supplied then the Attribute
  will not be writeable

.. note:: We are producing an `AttributeModel` rather than an `Attribute`.

    This is because the Attribute is a user facing View, with methods like
    :meth:`~Attribute.put_value`, while AttributeModel is a data centred model
    with methods like :meth:`~AttributeModel.set_value`. Each user gets their
    own `Attribute` view of a single underlying `AttributeModel` that holds the
    actual data.

In the two methods (zero and increment), we make use of the ``counter``
AttributeModel. We can get its value by using the :attr:`~AttributeModel.value`
attribute and set its value by calling the :meth:`~AttributeModel.set_value`
method. This method will validate the new value using the `VMeta` object we
created in ``__init__`` and notify any interested subscribers that something has
changed.

Visualising the Block with the GUI
----------------------------------

.. highlight:: ipython

There is a web GUI that ships with pymalcolm, called `malcolmjs`_. We can use it
to play with this counter block and see how it works. Let's launch our demo
again::

    [me@mypc pymalcolm]$ ./malcolm/imalcolm.py malcolm/modules/demo/DEMO-HELLO.yaml
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
        ['HELLO', 'HELLO2', 'COUNTER', 'WEB']

    Try:
    hello = self.block_view("HELLO")
    hello.greet("me")

    or

    gui(self.block_view("COUNTER"))

    or

    self.make_proxy("localhost:8008", "HELLO")
    self.block_view("HELLO").greet("me")


    In [1]:

Then open http://localhost:8008 in your favourite browser and click on the "..."
button next to "Select a root block" to select the **COUNTER** Block:

.. image:: counter_0.png

You will now see a representation of the **COUNTER** Block appear in the left
hand pane and the URL change to http://localhost:8008/gui/COUNTER:

.. image:: counter_1.png

If you try clicking the increment button a few times you should see the value
increase, the reset button should zero it and clicking on the counter value
should let you enter a number yourself. Clicking on the information icon next
to the counter value will give you a history of the values that the Attribute
has been set to.

Notice that the value we set counter to will also be validated by the meta
object we created, so you can enter ``34.5`` into the counter value, but if you
entered ``foo``, you will get a GUI that looks like this:

.. image:: counter_2.png

And a message on the console::

    malcolm.core.request: Exception raised for request Put(id=63, path=Array([u'COUNTER', u'counter']), value=u'foo', get=False)
    Traceback (most recent call last):
      File "./malcolm/../malcolm/core/controller.py", line 141, in _handle_request
        responses += handler(request)
      File "./malcolm/../malcolm/core/controller.py", line 196, in _handle_put
        value = attribute.meta.validate(request.value)
      File "./malcolm/../malcolm/core/models.py", line 551, in validate
        cast = self._np_type(value)
    ValueError: could not convert string to float: foo



Conclusion
----------

This second tutorial has taken us through creating Attributes in Blocks and
showed us a little bit of the error checking that `VMeta` instances
give us. Now we have a CounterPart, we could combine it with the HelloPart
from the previous tutorial, creating a Controller with 2 Parts that has
counter and ``greet()`` functionality. In the next tutorial we will see how
we can use this composition to control multiple child blocks with one parent
Block.

.. _malcolmjs: https://malcolmjs.readthedocs.io
