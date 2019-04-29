.. _supported_tags:

Supported Tags
==============

`tags_` are freeform text strings that appear in the tags field on Meta objects.
This page lists the currently supported tags, and how they are used.

Widget Tag
----------

.. module:: malcolm.core

A widget tag can be used to tell a GUI which widget to use to display an
Attribute. It is created by calling the :meth:`~Widget.tag` method on a
`Widget` enum member, like ``Widget.TEXTINPUT.tag()`` as introduced in the
`counter_tutorial`. It produces one of the following tags:

=========================== ====================================================
Tag                         Description
=========================== ====================================================
widget:textinput            Editable text input box
widget:textupdate           Read only text update
widget:multilinetextupdate  Multi line text update
widget:led                  On/Off LED indicator
widget:combo                Select from a number of choice values
widget:icon                 This field gives the SVG icon for the whole Block
widget:help                 Gives a URL for the help documentation for the Block
widget:group                | Expandable section that other Attributes can
                            | appear in
widget:table                Table of rows with a widget type for each column
widget:checkbox             A box that can be checked or not
widget:flowgraph            Boxes with lines for child block connections
widget:tree                 A nested tree of object models editor
=========================== ====================================================

Linked Value Tag
----------------

A Linked Value tag can be attached to an Attribute to tell the GUI that there
is another Attribute that can be monitored that should be displayed under the
current Attribute with the text "Linked Value". This is typically used for
inports whose connected outport tag contain a current value that could be
displayed. It is the responsibility of the Controller to change these tags if
the path to the Attribute that is to be displayed changes.

These are created using the `linked_value_tag`.

Port Tag
--------

The ``layout`` Attribute of a `ManagerController` is viewed with a FlowGraph
widget. This widget allows the child Blocks declared in the ``layout`` to
have a number of ``sourcePorts`` and ``sinkPorts`` which can be used to
visualize the connections between Blocks. The ``sourcePort`` Attribute tag
contains the value that a corresponding ``sinkPort`` should be set to when
the ports are connected. The ``sinkPort`` tag contains the value that the
``sinkPort`` should be set to when disconnected.

Port types
~~~~~~~~~~

The following port types are defined:

======= =======================================================================
Type    Description
======= =======================================================================
bool    Boolean value. Typically used in PandA
int32   32-bit signed integer. Typically used in PandA
NDArray areaDetector NDArray port
motor   Motor record connection to CS or controller
block   Malcolm level connection to another Block
======= =======================================================================

Source Port Tag
~~~~~~~~~~~~~~~

These are created on the child Attribute using the :meth:`~Port.source_port_tag`
method on the `Port` type enum member. The tag is
``sourcePort:<type>:<connected_value>`` where connected_value is the value that
a sinkPort should be set to when they are connected. For instance, a PandA
**CLOCKS** Block with an Attribute **A** that represents a produced clock would
use ``Port.BOOL.source_port_tag("CLOCKS.A")`` to create a tag
``sourcePort:bool:CLOCKS.A``

Sink Port Tag
~~~~~~~~~~~~~

These are created on the child Attribute using the :meth:`~Port.sink_port_tag`
method on the `Port` type enum member. The tag is
``sinkPort:<type>:<disconnected_value>`` where disconnected_value is the value
that the sinkPorts should be set to when disconnected from a sourcePort. For
instance, a PandA **PULSE** Block with an Attribute **INP** that represents
where it should get its input pulse train from would
use ``Port.BOOL.sink_port_tag("ZERO")`` to create a tag
``sinkPort:bool:ZERO``

Group Tag
---------

The ``widget:group`` tag on an Attribute creates a group expander area in the
GUI that other Attributes can appear in. They signify this by using the
`group_tag` function to create a ``group:<group_attribute_name>`` tag where
group_attribute_name is the name of the Attribute with the ``widget:group``
tag on it. For instance if the ``outputs`` Attribute has a ``widget:group`` tag
on it, other Attributes could appear in the outputs group expander by adding a
``group:outputs`` tag.

Config Tag
----------

A config tag on an Attribute marks a field as one that should be saved and
loaded by a parent `ManagerController`. These are created by using the
`config_tag` function to create a ``config:<iteration>`` tag where iteration
is a positive number. Loading of attributes takes place in a number of
iterations, starting with the lowest number, with all Attributes in a single
iteration being set simultaneously.

Method Return Unpacked Tag
--------------------------

A ``method:return:unpacked`` tag is created using the `method_return_unpacked`
function. Its purpose is defined in the docstring:

.. autofunction:: malcolm.core.method_return_unpacked
    :noindex:

