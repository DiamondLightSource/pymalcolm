.. _statesets:

State Sets and Hooks
====================

If a malcolm Block has a ``state`` attribute, its controller has a StateSet that
controls the valid transitions that it can make. These are arranged in a
heirarchy.

StatefulController
------------------

A `StatefulController` has Ready, Fault and Disable states. It is used in blocks
in the `hardware_layer_`. It implements the following statemachine:

.. autoclass:: malcolm.modules.builtin.util.StatefulStates
    :noindex:

    .. graphviz:: ../build/builtin/stateful_states.dot

The following `Hooks <hook_>` are run during state transitions:

.. automodule:: malcolm.modules.builtin.hooks
    :noindex:
    :members: InitHook, HaltHook, ResetHook, DisableHook

ManagerController
-----------------

A `ManagerController` adds Loading/Saving. It is used in simple blocks in the
`device_layer_`. It implements the following statemachine:

.. autoclass:: malcolm.modules.builtin.util.ManagerStates
    :noindex:

    .. graphviz:: ../build/builtin/manager_states.dot

The following `Hooks <hook_>` are run during state transitions:

.. automodule:: malcolm.modules.builtin.hooks
    :noindex:
    :members: LayoutHook, LoadHook, SaveHook

RunnableController
------------------

A `RunnableController` adds Configuring/Running/Aborting/Seeking. It is used in
blocks that support scans in the `device_layer_` or `scan_layer_`. It implements
the following statemachine:

.. autoclass:: malcolm.modules.scanning.util.RunnableStates
    :noindex:

    .. graphviz:: ../build/scanning/runnable_states.dot

The following `Hooks <hook_>` are run during state transitions:

.. automodule:: malcolm.modules.scanning.hooks
    :noindex:
    :members:
