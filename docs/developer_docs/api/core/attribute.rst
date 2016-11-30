.. _Attribute:

Attribute
---------

An Attribute holds a value such as an Int, Float or Enum Table representing
the current state of a block.

Hold the current value of a piece of data of a fixed simple type
like Int, Float, String, Enum, IntArray or Table. You can Get and Subscribe to
changes in all Attributes, and Put to Attributes with a defined setter. In a
client Block, Attributes will mirror the value of the Block acting as a
server, with a Put operation being forwarded to the server Block. For example,
the State of a Block would be an Attribute, as would the CurrentStep of a
scan.

Subclasses serialize differently.

.. module:: malcolm.core

.. autoclass:: Attribute
    :members: