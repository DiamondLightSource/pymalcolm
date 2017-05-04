MethodModel
-----------

.. module:: malcolm.core

.. autoclass:: MethodModel
    :members:

    A Method exposes a function call for a Block:

    Expose a function call. You can Call a Method with a (possibly empty)
    Map of arguments, and it will return a (possibly empty) Map of return values.
    In a client Block, the Call will be forwarded to the server Block, and the
    return value returned to the caller. For example, configure() and run() would
    be Methods of a Blocks used in a mapping scan.

.. data:: REQUIRED

    Used to mark an argument in method_takes() or method_returns() as required

.. data:: OPTIONAL

    Used to mark an argument in method_takes() or method_returns() as optional

.. autofunction:: method_takes

.. autofunction:: method_returns
