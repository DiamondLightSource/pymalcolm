.. _statesets:

State Sets
==========

If a malcolm Block has a ``state`` attribute, its controller has a StateSet that
controls the valid transitions that it can make. These are arranged in a
heirarchy.

- `StatefulStates` - Ready, Fault, Disable. Used in blocks in the
    `hardware_layer_`
- `ManagerStates` - Adds Load, Save. Used in cut down blocks in the
    `device_layer_`
- `RunnableStates` - Adds Configuring, Running, Seeking. Used in a regular
    blocks in the `device_layer_` or `scan_layer_`
