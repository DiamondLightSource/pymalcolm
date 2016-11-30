.. _Block:

Block
-----

A Block consists of number of Attributes and Methods:

An object consisting of a number of Attributes and Methods. It should
be designed to be as small and self contained as possible, and complex logic
should be implemented by nesting Blocks. For example, a detector driver would
be a Block, as would an HDF writer, but there would also be a higher level
detector Block to co-ordinate the low level Blocks. Any Block may be
synchronized among a number of Processes, the Block acting as the server will
perform the logic, and the client copies will expose the same API as the
server Block to the end user.

.. module:: malcolm.core

.. autoclass:: Block
    :members: