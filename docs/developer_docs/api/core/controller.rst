.. _Controller:

Controller
----------

Controller: A State Machine just exposes the list of allowed transitions
between States. The Controller provides the logic that goes behind those
transitions. It creates a number of Methods fixing the external interface of
how to control the blocks, creates some Attributes for monitoring
configuration and runtime variables, and then exposes a number of hooks that
Parts can utilise to be executed and control transition to other states. For
example, there will be an AreaDetectorController with hooks for
PreRunDriverStart, PreRunPluginStart, and Running.

A Controller implements the logic for changing states and contains Hooks for
allow Parts to run any functions that are relevant to the current transition:

.. module:: malcolm.core

.. autoclass:: Controller
    :members: