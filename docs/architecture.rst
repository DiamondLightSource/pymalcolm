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

Every state machine in Malcolm will include the following states. BlockSpecific
is a placeholder for the states that will be different for each implementation
of a Block.

.. uml::
    !include docs/stateMachineDefs.iuml

    state canDisable {
        state canError {
            state canAbort {
                Resetting --> BlockSpecific

                state BlockSpecific <<Rest>>
            }
            canAbort --> Aborting : Abort

            state Aborting <<Abort>>
            Aborting --> Aborted
            Aborted --> Resetting : Reset
        }
        canError -right-> Fault : Error

        state Fault <<Fault>>
        Fault --> Resetting : Reset
    }
    canDisable -right-> Disabled : Disable

    state Disabled <<Disabled>>
    Disabled --> Resetting : Reset

Default State Machine
~~~~~~~~~~~~~~~~~~~~~

If no state machine is specified, the following will be used:

.. uml::
    !include docs/stateMachineDefs.iuml

    Resetting -down-> Ready

    state Ready <<Rest>>

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

    Resetting -down-> Idle
    state Idle <<Rest>>
    Idle -right-> Configuring : Configure
    Configuring -right-> Ready
    state Ready <<Rest>>
    Ready -right-> PreRun : Run
    PreRun -right-> Running
    Running -right-> PostRun
    PostRun --> Ready
    PostRun -left-> Idle

Pausable Device State Machine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

More sophisticated mapping devices have the same state machine as
RunnableDevice, but include some pausing states. These allow a Run to be paused
by the user, and rewound once it has become paused.

.. uml::
    !include docs/stateMachineDefs.iuml

    Resetting -down-> Idle
    state Idle <<Rest>>
    Idle -right-> Configuring : Configure
    Configuring -right-> Ready
    state Ready <<Rest>>
    Ready -right-> PreRun : Run
    PreRun -right-> Running
    Running -right-> PostRun
    PostRun --> Ready
    PostRun -left-> Idle

    PreRun -down-> Pausing : Pause
    Running -down-> Pausing : Pause
    PostRun -down-> Pausing : Pause
    Pausing -left-> Rewinding
    Paused -right-> Rewinding : Rewind
    Ready -down-> Rewinding : Rewind
    Rewinding -left-> Paused
    Rewinding -up-> Ready




Blocks and Parts
----------------

How Blocks are made by composition, and some examples of the ini file format

Messages and types
------------------

Threading Model
---------------

Generators
----------



