Architecture
============

Malcolm can be considered to be a distributed object system. This document will
use a number of terms to identify key components of Malcolm:

- Process: A Malcolm instance containing a number of Blocks along with various
  communication modules to communicate with other Malcolm instances. A Process
  can be a client of or a server to a number of other Processes.
- Block: An object consisting of a number of Attributes and Methods. It should
  be designed to be as small and self contained as possible, and complex logic
  should be implemented by nesting Blocks. For example, a detector driver would
  be a Block, as would an HDF writer, but there would also be a higher level
  detector Block to co-ordinate the low level Blocks. There would then be a top
  level mapping scan Block the co-ordinated the detector Block and a motion
  trajectory block to perform the scan. Any Block may be synchronized among a
  number of Processes, the Block acting as the server will perform the logic,
  and the client copies will expose the same API as the server Block to the end
  user.
- Attributes: Hold the current value of a piece of data of a fixed simple type
  like Int, Float, String, Enum, IntArray, Table or a named Map. You can Get
  and Subscribe to changes in all Attributes, and Put to Attributes with a
  defined setter. In a client Block, Attributes will mirror the value of the
  Block acting as a server, with a Put operation being forwarded to the server
  Block.
- Methods: Expose a function call. You can Call a Method with a (possibly empty)
  Map of arguments, and it will return a (possibly empty) Map of return values.
  In a client Block, the Call will be forwarded to the server Block, and the
  return value returned to the caller.

For example, in the following diagram, Process1 is hosting two Blocks, and
Process2 has a client of Block 2 as a local object.

.. uml::

    frame Process1 {
        frame Block1 {
            [Attribute 1]
            [Attribute 2]
            [Method 1]
        }

        frame Block2 {
            [Attribute 1] as B2.A1
            [Method 1] as B2.M1
        }
    }

    frame Process2 {
        frame Block2Client {
            [Attribute 1] as B2C.A1
            [Method 1] as B2C.M1
        }
    }

    B2C.A1 --> B2.A1
    B2C.M1 --> B2.M1


Block Structure
---------------

To describe how a Block is structured, we will use the `pvData Meta Language`_.
It is important to note that although many EPICS conventions are followed in
Malcolm, it is not a required part of it.

.. _pvData Meta Language:
    http://epics-pvdata.sourceforge.net/docbuild/pvDataJava/tip/documentation/
    pvDataJava.html#pvdata_meta_language

A Block looks like this::

    Block :=
        string      descriptor  // Description of Block
        string[]    tags        // e.g. "instance:FlowGraph"
        Attribute   state       // type=enum
        Attribute   status      // type=string
        Attribute   busy        // type=bool
        {Attribute  <attribute-name>}0+
        {Method     <method-name>}0+

The `state` Attribute corresponds to the state described in the `State Machine`_
section below. The `status` Attribute will hold any status message that is
reported by the Block, for instance reporting on the progress through a long
running activity. The `busy` Attribute will be true if the state is not a Rest
state as defined below.

An Attribute looks like this::

    Attribute := NTScalar | NTScalarArray | Table | Map

    NTScalar :=
        scalar_t    value
        alarm_t     alarm
        time_t      timeStamp
        ScalarMeta  meta

    NTScalarArray :=
        scalar_t[]  value
        alarm_t     alarm
        time_t      timeStamp
        ScalarMeta  meta

    Table :=
        structure   value
            {scalar_t[] <colname>}0+
        alarm_t     alarm
        time_t      timeStamp
        MapMeta     meta

    Map :=
        structure   value
            {NTScalar | NTScalarArray | Table <keyname>}0+
        MapMeta     meta

The structures are very similar, and all hold the current value in whatever
type is appropriate for the Attribute. Each structure contains a `meta` field
that describes the values that are allowed to be passed to the value field of
the structure::

    ScalarMeta :=
        string      descriptor      // Description of attribute
        string      type            // one of scalar_t or scalar_t[] strings
                                    // or "enum" or "enum[]"
        bool        writeable  :opt // True if you can Put
        string[]    tags       :opt // e.g. "widget:textinput"
        display_t   display    :opt // Display limits, units, etc, for numbers
        control_t   control    :opt // For writeable numbers
        string[]    labels     :opt // Allowed values if type is "enum"

    MapMeta :=
        string      descriptor      // Description of attribute
        string      type            // "map" or "table"
        bool        writeable  :opt // True if you can Put
        structure   elements
            {ScalarMeta | MapMeta <argname>}0+
        string[]    tags      :opt  // e.g. "widget:group"
        string[]    required  :opt  // If specified, only these fields are
                                    // required, otherwise all are
        string[]    labels    :opt  // List of column labels if different to
                                    // arguments members

ScalarMeta has a number of fields that will be present or not depending on the
contents of the type field. MapMeta contains a structure of elements that
describe the subelements that are allowed in the Map (or Table).

A Method looks like this::

    Method :=
        string      descriptor          // Docstring
        MapMeta     takes               // Argument spec
        structure   defaults
            {any    <argname>}0+        // The defaults if not supplied
        MapMeta     returns             // Return value spec

The takes structure describes the arguments that can be 




State Machine
-------------

There is a general purpose state machine that every Malcolm Block has. It covers
the aborting, fault monitoring, and disabling of the Block. Every Block then
has a specific state machine that allows for the more specialised states that
make sense for the block. The general purpose state machine is shown here,
along with the simplest "Ready" state machine, and two variants of the
configure/run state machine that are used for mapping scans.

General Purpose States
^^^^^^^^^^^^^^^^^^^^^^

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
            BlockStates : transition to. May contain block specific states

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
^^^^^^^^^^^^^^^^^^^^^

If no state machine is specified, the following will be used:

.. uml::
    !include docs/stateMachineDefs.iuml

    Resetting -left-> Ready

    state Ready <<Rest>>
    Ready : Rest state

Runnable Device State Machine
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
    PostRun -left-> Ready
    PostRun -left-> Idle
    Ready --> Resetting : Reset
    Ready : Rest state

Pausable Device State Machine
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
    PostRun -left-> Ready
    PostRun -left-> Idle
    Ready --> Resetting : Reset
    Ready : Rest state

    Running -down-> Pausing : Pause
    PreRun -down-> Pausing : Pause
    Pausing -right-> Paused
    Paused -left-> Pausing : Rewind
    Ready -down-> Rewinding : Rewind
    Rewinding -up-> Ready
    Paused -up-> Running : Resume

Blocks and Parts
----------------

Messages and types
------------------

Threading Model
---------------

Generators
----------



