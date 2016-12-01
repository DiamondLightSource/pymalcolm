StateMachine
------------

.. module:: malcolm.core

.. autoclass:: StateMachine
    :members:

    State Machine: Every Malcolm Block contains a State Machine that maps the
    allowed transitions between different values of the State Attribute. This
    allows external applications to monitor what a Block is doing, and gives a
    condition for whether particular Methods can run or not. See the
    `statemachine_diagrams` section for examples.

.. autoclass:: DefaultStateMachine
    :members:

.. autoclass:: ManagerStateMachine
    :members:

.. autoclass:: RunnableStateMachine
    :members:

