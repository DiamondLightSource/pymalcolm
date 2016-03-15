Architecture
============

Overview of what the significant parts of Malcolm are:

- Blocks
- Attributes
- Methods

State Machine
-------------

There is a general purpose state machine that every Malcolm Block has. It covers
the aborting, fault monitoring, and disabling of the Block. Every Block then
has a specific state machine that allows for the more specialised states that
make sense for the block. The general purpose state machine is shown here,
along with the simplest "Ready" state machine, and two variants of the
configure/run state machine that are used for mapping scans.

General Purpose States
~~~~~~~~~~~~~~~~~~~~~~

Every state machine in Malcolm will include the following states. BlockStates
is a placeholder for the states that will be different for each implementation
of a Block.

.. uml::
    !include docs/stateMachineDefs.iuml

    state canDisable {
        state canError {
            state BlockStates {
                state ___ <<Rest>>
                ___ : Rest state
                Resetting -left-> ___
            }

            BlockStates : Has one or more Rest states that Resetting can
            BlockStates : transition to. May contain other block specific states

            BlockStates -down-> Aborting : Abort
            Aborting -right-> Aborted
            state Aborted <<Abort>>
            Aborted : Rest state
            Aborted -up-> Resetting : Reset
        }
        canError -right-> Fault : Error

        state Fault <<Fault>>
        Fault : Rest state
        Fault --> Resetting : Reset
    }
    canDisable --> Disabled : Disable

    state Disabled <<Disabled>>
    Disabled : Rest state
    Disabled --> Resetting : Reset
    [*] -right-> Disabled


Default State Machine
~~~~~~~~~~~~~~~~~~~~~

If no state machine is specified, the following will be used:

.. uml::
    !include docs/stateMachineDefs.iuml

    Resetting -left-> Ready

    state Ready <<Rest>>
    Ready : Rest state

Runnable Device State Machine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The simplest mapping devices have a configure() method that allows the batch
setting of a number of parameters, and can safely be called on a number of
devices concurrently. They then have a run() method that kicks off a scan. The
PreRun and PostRun states are guaranteed to be transitioned through, and denote
the times when the run has started (or finished), but the device is not
currently active. For example, when a detector has been started but is waiting
for a hardware signal, or when the detector has finished all its exposures and
data is being flushed to disk.

.. uml::
    !include docs/stateMachineDefs.iuml

    Resetting --> Idle
    state Idle <<Rest>>
    Idle : Rest state
    Idle -right-> Configuring : Configure
    Configuring -right-> Ready
    state Ready <<Rest>>
    Ready -right-> PreRun : Run
    PreRun -right-> Running
    Running -right-> PostRun
    PostRun --> Ready
    PostRun -left-> Idle
    Ready --> Resetting : Reset
    Ready : Rest state

Pausable Device State Machine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

More sophisticated mapping devices have the same state machine as
RunnableDevice, but include some pausing states. These allow a Run to be paused
by the user, and rewound once it has become paused.

.. uml::
    !include docs/stateMachineDefs.iuml

    Resetting --> Idle
    state Idle <<Rest>>
    Idle : Rest state
    Idle -right-> Configuring : Configure
    Configuring -right-> Ready
    state Ready <<Rest>>
    Ready -right-> PreRun : Run
    PreRun -right-> Running
    Running -right-> PostRun
    PostRun --> Ready
    PostRun -left-> Idle
    Ready --> Resetting : Reset
    Ready : Rest state

    Running -down-> Pausing : Pause
    PreRun -down-> Pausing : Pause
    Pausing -right-> Paused
    Paused -left-> Pausing : Rewind
    Ready -down-> Rewinding : Rewind
    Rewinding -up-> Ready
    Paused --> Running : Resume




Blocks and Parts
----------------

How Blocks are made by composition, and some examples of the ini file format

Messages and types
------------------

Threading Model
---------------

Generators
----------



