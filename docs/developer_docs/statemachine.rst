State Machine
=============

There is a general purpose state machine that every Malcolm Block has. It covers
the aborting, fault monitoring, and disabling of the Block. Every Block then
has a specific state machine that allows for the more specialised states that
make sense for the block. The general purpose state machine is shown here,
along with the simplest "Ready" state machine, and two variants of the
configure/run state machine that are used for mapping scans.

General Purpose States
----------------------

Every state machine in Malcolm will include the following states. BlockStates
is a placeholder for the states that will be different for each implementation
of a Block. Unlabelled transitions take place in response to internal actions,
labelled transitions are triggered externally.

.. uml::

    !include docs/style.iuml

    state BlockStates {
        state ___ <<Rest>>
        ___ : Rest state

        Resetting -left-> ___
    }
    BlockStates : Has one or more Rest states that Resetting can
    BlockStates : transition to. May contain block specific states
    BlockStates -down-> Fault : Error
    BlockStates -down-> Disabling : Disable
    Disabling --> Disabled
    Disabling -left-> Fault: Error

    state Fault <<Fault>>
    Fault : Rest state
    Fault -up-> Resetting : Reset
    Fault --> Disabled : Disable

    state Disabled <<Disabled>>
    Disabled : Rest state
    Disabled -up-> Resetting : Reset
    [*] -right-> Disabled

Default State Machine
---------------------

If no state machine is specified, the following will be used:

.. uml::

    !include docs/style.iuml

    state BlockStates {
        state Ready <<Rest>>
        Ready : Rest state

        Resetting -left-> Ready
    }

.. _manager-state-machine:

Manager State Machine
---------------------

Manager blocks are responsible for wiring child blocks. It can be edited, and
will allow saving and reverting these changes to take it back to a Ready state.

.. uml::

    !include docs/style.iuml

    state BlockStates {
        state Ready <<Rest>>
        Ready : Rest state

        Ready -up-> Editing : Edit
        Editing -up-> Editable
        Editable -down-> Saving : Save
        Editable -down-> Reverting : Revert
        Saving -down-> Ready
        Reverting -down-> Ready
    }

There are some standard methods that Manager Blocks have:

- edit() - Start editing the child blocks of this block (normally via web gui)
- save() - Save the edited state and move back to Idle
- revert() - Discard any edited modifications and take it back to how it was

Runnable State Machine
----------------------

Mapping devices have a configure() method that allows the batch setting of a
number of parameters, and can safely be called on a number of devices
concurrently. Motion may occur during the Configuring state as devices are moved
to their start positions. They then have a run() method that kicks off a scan.
The PreRun and PostRun states are guaranteed to be transitioned through, and
denote the times when the run has started (or finished), but the device is not
currently taking data. For example, when a detector has been started but is
waiting for a hardware signal, or when the detector has finished all its
exposures and data is being flushed to disk. Motion flyback may occur in the
PostRun state if it is specified for the scan. They also have some pausing
states. These allow a Run to be paused by the user, and rewound once it has
become paused.

.. uml::

    !include docs/style.iuml

    state BlockStates {
        state NormalStates {
            Resetting --> Idle

            state Idle <<Rest>>
            Idle : Rest state
            Idle -right-> Configuring : Configure

            Configuring -right-> Ready

            state Ready <<Rest>>
            Ready : Rest state
            Ready -right-> PreRun : Run
            Ready --> Resetting : Reset
            Ready -down-> Rewinding : Rewind

            PreRun -right-> Running
            PreRun -down-> Rewinding : Pause

            Running -right-> PostRun
            Running -down-> Rewinding : Pause

            PostRun -left-> Ready
            PostRun -left-> Idle

            Rewinding -right-> Paused

            Paused -left-> Rewinding : Rewind
            Paused -up-> PreRun : Resume
        }

        NormalStates -down-> Aborting : Abort

        Aborting -left-> Aborted

        state Aborted <<Abort>>
        Aborted : Rest state
        Aborted -up-> Resetting : Reset

        Idle -up-> Editing : Edit
        Editing -up-> Editable
        Editable -down-> Saving : Save
        Editable -down-> Reverting : Revert
        Saving -down-> Idle
        Reverting -down-> Idle
    }

There are some standard methods that Runnable Blocks have:

- validate(params) - Check for a consistent set of parameters, filling in any
  defaults, and adding time and timeout estimates
- configure(params) - Configure a device for a scan so it is ready to run
- run() - Run the configured scan
- pause() - Gracefully stop the scan at the next convenient place
- retrace(steps) - Move back at least this number of scan steps
- resume() - Resume a paused scan
- abort() - Stop any activity
- disable() - Disable device, stopping all activity
- reset() - Reset the device, moving it back into Idle state after
  error, abort or disable

Runnable Block Methods
----------------------

Apart from validate(), all other methods take the block through some state
transitions. These are listed below for each method.

validate(params)
^^^^^^^^^^^^^^^^

This method is meant to be called by GDA to check whether a given set of
parameters is valid or not. Some parameters are required and some have defaults,
and this information can be introspected as detailed later on. Each set of
parameters is checked for validity in isolation, no device state is taken into
account, so if a number of scans are queued by the user, GDA could check each
for validity by running this function on each set of params in turn.

configure(params)
^^^^^^^^^^^^^^^^^

This method will call validate(params), then use these params to configure the
device ready for a run. This action will try to prepare the device as much as
possible so that run() is quick to start. This means that it may move motors to
put the device in the correct starting condition. It is allowed from the Idle
state, and will block until the device is in a rest state. Normally it will
return in Ready state. If the user aborts then it will return in Aborted state.
If something goes wrong it will return in Fault state. If the user disable
then it will return in Disabled state.

The state diagram subset below shows the valid set of transitions:

.. uml::

    !include docs/style.iuml

    state NormalStates {
        state Idle <<Rest>>
        Idle : Start state
        Idle -right-> Configuring : Configure

        Configuring -right-> Ready

        state Ready <<Rest>>
        Ready : End state
    }

    !include docs/arch/stateMachineNotNormal.iuml

run()
^^^^^

This method will run a device that has been configured for a scan. It is allowed
from the Ready or Paused states, and will block until the device is in a rest
state. Normally it will return in Idle state. If the device allows many runs
from a single configure, then it will return in Ready state. If the user aborts
then it will return in Aborted state. If the user pauses then it will return in
Paused state. If something goes wrong it will return in Fault state. If the
user disable then it will return in Disabled state.

The state diagram subset below shows the valid set of transitions:

.. uml::

    !include docs/style.iuml

    state NormalStates {
        state Idle <<Rest>>
        Idle : End state

        state Ready <<Rest>>
        Ready : Start state
        Ready : End state
        Ready -right-> PreRun : Run

        PreRun -right-> Running
        PreRun -down-> Rewinding : Pause

        Running -right-> PostRun
        Running -down-> Rewinding : Pause

        PostRun -left-> Ready
        PostRun -right-> Idle

        Rewinding -right-> Paused

        Paused -left-> Rewinding : Rewind
        Paused -up-> PreRun : Resume

    }

    !include docs/arch/stateMachineNotNormal.iuml

pause()
^^^^^^^

This method will pause a run so that it can be resumed later. It is allowed from
the Running state and will block until the device is Aborted, Fault or Paused.
Normally it will return in Paused state. If the user aborts then it will return
in Aborted state. If something goes wrong it will return in Fault state. If the
user disable then it will return in Disabled state.

The state diagram subset below shows the valid set of transitions:

.. uml::

    !include docs/style.iuml

    state NormalStates {
        PreRun -down-> Rewinding : Pause
        PreRun : Start state

        Running -down-> Rewinding : Pause
        Running : Start state

        Rewinding -right-> Paused

        Paused : End state
    }

    !include docs/arch/stateMachineNotNormal.iuml

retrace(steps)
^^^^^^^^^^^^^^

This method will retrace a number of steps in the scan so that when it is
resumed it will overwrite invalid data that may have been acquired before
pause(). It will retrace by at least as many steps as demanded. It is allowed
from the Paused state and will block until the device is Paused again. Normally
it will return in Paused state. If the user aborts then it will return in
Aborted state. If something goes wrong it will return in Fault state. If the
user disable then it will return in a Disabled state.

The state diagram subset below shows the valid set of transitions:

.. uml::

    !include docs/style.iuml

    state NormalStates {
        Paused -left-> Rewinding : Rewind
        Paused : Start state
        Paused : End state

        Rewinding -right-> Paused

        state Ready <<Rest>>
        Ready -down-> Rewinding : Rewind
        Ready : Start state
    }

    !include docs/arch/stateMachineNotNormal.iuml


resume()
^^^^^^^^

This method will resume a paused scan. It is allowed from the Paused state and
will transition the device to PreRun state and return immediately.

The state diagram subset below shows the valid set of transitions:

.. uml::

    !include docs/style.iuml

    state NormalStates {
        state Paused
        Paused -up-> PreRun : Resume
        Paused : Start state

        PreRun : End state
    }

abort()
^^^^^^^

This method will abort a configure or abandon the scan whether it is running or
paused. It is allowed from any normal block state, and will block until the
device is in a rest state. Normally it will return in Aborted state. If
something goes wrong it will return in Fault state.  If the used disable
then it will return in a Disabled state.

The state diagram subset below shows the valid set of transitions:

.. uml::

    !include docs/style.iuml

    NormalStates : Start state
    NormalStates :
    NormalStates : Abort is allowed from
    NormalStates : any normal block state
    NormalStates --> Aborting : Abort

    Aborting -left-> Aborted
    Aborting -right-> Disabling : Disable
    Aborting -down-> Fault : Error

    Disabling -down-> Disabled
    Disabling -left-> Fault : Error

    state Aborted <<Abort>>
    Aborted : End state

    state Fault <<Fault>>
    Fault : End state

    state Disabled <<Disabled>>
    Disabled : End state

disable()
^^^^^^^^^

This method will stop the block responding to external input until reset() is
called. It is allowed from any state, and will mark the device as Disabled and
return immediately. It will always return in Disabled state.

The state diagram subset below shows the valid set of transitions:

.. uml::

    !include docs/style.iuml

    BlockStates : Start state
    BlockStates :
    BlockStates : Disable is allowed from
    BlockStates : any block state
    BlockStates --> Disabling : Disable

    Disabling -right-> Disabled
    Disabling -left-> Fault : Error

    state Fault <<Fault>>
    Fault : End state

    state Disabled <<Disabled>>
    Disabled : End state


reset()
^^^^^^^

This method will reset the device, putting it into Idle state. It is allowed
from Aborted, Disabled, Ready or Fault states, and will block until the device
is in a rest state. Normally it will return in Idle state. If something goes
wrong it will return in Fault state.

The state diagram subset below shows the valid set of transitions:

.. uml::

    !include docs/style.iuml

    state NormalStates {
        state Idle <<Rest>>
        Idle : End state

        state Ready <<Rest>>
        Ready -left-> Resetting : Reset
        Ready : Start state

        Resetting -left-> Idle
    }

    Disabling -down-> Disabled
    Disabling --> Fault : Error

    Resetting -down-> Aborting : Abort
    Resetting -down-> Disabling : Disable
    Resetting --> Fault : Error

    Aborting --> Aborted
    Aborting --> Fault : Error

    state Aborted <<Abort>>
    Aborted : Start state
    Aborted : End state
    Aborted -up-> Resetting : Reset

    state Fault <<Fault>>
    Fault : Start state
    Fault : End state
    Fault -up-> Resetting : Reset

    state Disabled <<Disabled>>
    Disabled : Start state
    Disabled : End state
    Disabled -up-> Resetting : Reset


edit()
^^^^^^

This method will start editing the child blocks of this block (normally via web
gui), putting it into an Editing state. It is allowed from the Idle state, and
will block until the device is in a rest state. Normally it will return in Idle
state. If something goes wrong it will return in Fault state.

The state diagram subset below shows the valid set of transitions:

.. uml::

    !include docs/style.iuml

    state BlockStates {

        state Idle <<Rest>>
        Idle : Start state
        Idle : End state

        Idle -up-> Editing : Edit
        Editing -down-> Saving : Save
        Editing -down-> Reverting : Revert
        Saving -down-> Idle
        Reverting -down-> Idle
    }

    !include docs/arch/stateMachineNotBlock.iuml


save()
^^^^^^

This method will save the current state of child blocks of this block (normally
via web gui), putting it back into an Idle state. It is allowed from the Editing
state, and will block until the device is in a rest state. Normally it will
return in Idle state. If something goes wrong it will return in Fault state.

The state diagram subset below shows the valid set of transitions:

.. uml::

    !include docs/style.iuml

    state BlockStates {

        state Idle <<Rest>>
        Idle : End state

        state Editing
        Editing : Start state

        Editing -down-> Saving : Save
        Saving -down-> Idle
    }

    !include docs/arch/stateMachineNotBlock.iuml

revert()
^^^^^^^^

This method will discard any edited modifications and take it back to how it was
before editing started, putting it back into an Idle state. It is allowed from
the Editing state, and will block until the device is in a rest state. Normally
it will return in Idle state. If something goes wrong it will return in Fault
state.

The state diagram subset below shows the valid set of transitions:

.. uml::

    !include docs/style.iuml

    state BlockStates {

        state Idle <<Rest>>
        Idle : End state

        state Editing
        Editing : Start state

        Editing -down-> Reverting : Revert
        Reverting -down-> Idle
    }

    !include docs/arch/stateMachineNotBlock.iuml



