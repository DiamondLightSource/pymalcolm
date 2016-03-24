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
        Attribute   state       // type=enum
        Attribute   status      // type=string
        Attribute   busy        // type=bool
        {Attribute  <attribute-name>}0+
        {Method     <method-name>}0+
        BlockMeta   meta

    BlockMeta :=
        string      description  // Description of Block
        string[]    tags        // e.g. "instance:FlowGraph"

The `state` Attribute corresponds to the state described in the `State Machine`_
section below. The `status` Attribute will hold any status message that is
reported by the Block, for instance reporting on the progress through a long
running activity. The `busy` Attribute will be true if the state is not a Rest
state as defined below.

An Attribute looks like this::

    Attribute := NTScalar | NTScalarArray | Table

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
        TableMeta   meta

The structures are very similar, and all hold the current value in whatever
type is appropriate for the Attribute. Each structure contains a `meta` field
that describes the values that are allowed to be passed to the value field of
the structure::

    ScalarMeta :=
        string      description     // Description of attribute
        string      type            // one of scalar_t or scalar_t[] strings
                                    // or "enum" or "enum[]"
        bool        writeable  :opt // True if you can Put
        string[]    tags       :opt // e.g. "widget:textinput"
        display_t   display    :opt // Display limits, units, etc, for numbers
        control_t   control    :opt // For writeable numbers
        string[]    oneOf      :opt // Allowed values if type is "enum"
        string      label      :opt // Short label if different to name

    TableMeta :=
        string      description     // Description of attribute
        structure   elements        // Metadata for each column, must have array
            {ScalarMeta <elname>}0+ // type
        bool        writeable  :opt // True if you can Put
        string[]    tags       :opt // e.g. "widget:table"
        string[]    labels     :opt // List of column labels if different to
                                    // element names

ScalarMeta has a number of fields that will be present or not depending on the
contents of the type field. TableMeta contains a structure of elements that
describe the subelements that are allowed in the Table.

Where do we put versions?

A Method looks like this::

    MapMeta :=
        structure   elements        // Metadata for each element in map
            {ScalarMeta | TableMeta <elname>}0+
        string[]    tags       :opt // e.g. "widget:group"
        string[]    required   :opt // These fields will always be present

    Method :=
        string      description     // Docstring
        MapMeta     takes           // Argument spec
        structure   defaults
            {any    <argname>}0+    // The defaults if not supplied
        MapMeta     returns    :opt // Return value spec if any

The `takes` structure describes the arguments that should be passed to the
Method. The `returns` structure describes what will be returned as a result.
The `defaults` structure contains default values that will be used if the
argument is not supplied.

There will be typeids on each element with versions so that we can fix call
signatures etc.

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
    Ready : Rest state
    Ready -right-> PreRun : Run
    Ready --> Resetting : Reset

    PreRun -right-> Running

    Running -right-> PostRun

    PostRun -left-> Ready
    PostRun -left-> Idle


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
    Ready : Rest state
    Ready -right-> PreRun : Run
    Ready --> Resetting : Reset
    Ready -down-> Rewinding : Rewind

    PreRun -right-> Running
    PreRun -down-> Pausing : Pause

    Running -right-> PostRun
    Running -down-> Pausing : Pause

    PostRun -left-> Ready
    PostRun -left-> Idle

    Pausing -right-> Paused

    Paused -left-> Pausing : Rewind
    Paused -right-> Resuming : Resume

    Resuming -up-> Running

    Rewinding -up-> Ready

Runnable and Pausable Device Methods
------------------------------------

There are some standard methods that Runnable and Pausable Devices have:

- validate(params) - Check for a consistent set of paraemeters, filling in any
  defaults, and adding time and timeout estimates
- configure(params) - Configure a device for a scan so it is ready to run
- run() - Run the configured scan
- pause() - Gracefully stop the scan at the next convenient place
- retrace(steps) - Move back at least this number of scan steps
- resume() - Resume a paused scan
- abort() - Stop any activity
- disable() - Deactivate device
- reset() - Reset the device back into Idle state after error, abort or disable

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
If something goes wrong it will return in Fault state. If the user disables
then it will return in Disabled state. The state diagram subset below shows the
valid set of transitions:

.. uml::
    !include docs/stateMachineDefs.iuml

    state NormalStates {
        state Idle <<Rest>>
        Idle : Start state
        Idle -right-> Configuring : Configure

        Configuring -right-> Ready

        state Ready <<Rest>>
        Ready : End state
    }
    NormalStates --> Aborting : Abort
    NormalStates --> Fault : Error
    NormalStates --> Disabled : Disable

    Aborting -left-> Aborted
    Aborting -right-> Fault : Error

    state Aborted <<Abort>>
    Aborted : End state

    state Fault <<Fault>>
    Fault : End state

    state Disabled <<Disabled>>
    Disabled : End state

run()
^^^^^

This method will run a device that has been configured for a scan. It is allowed
from the Ready or Paused states, and will block until the device is in a rest
state. Normally it will return in Idle state. If the device allows many runs
from a single configure, then it will return in Ready state. If the user aborts
then it will return in Aborted state. If the user pauses then it will return in
Paused state. If something goes wrong it will return in Fault state. If the
user disables then it will return in Disabled state. The state diagram subset
below shows the valid set of transitions:

.. uml::
    !include docs/stateMachineDefs.iuml

    state NormalStates {
        state Ready <<Rest>>
        Ready : Start state
        Ready : End state
        Ready -right-> PreRun : Run

        PreRun -right-> Running
        PreRun -down-> Pausing : Pause

        Running -right-> PostRun
        Running -down-> Pausing : Pause

        PostRun -left-> Ready
        PostRun -left-> Idle

        Pausing -right-> Paused

        Paused -left-> Pausing : Rewind
        Paused -right-> Resuming : Resume

        Resuming -up-> Running

        state Idle <<Rest>>
        Idle : End state
    }

    !include docs/stateMachineNotNormal.iuml

pause()
^^^^^^^

If this method is available then the device is a PausableDevice. This method
will pause a run so that it can be resumed later. It is allowed from the Running
state and will block until the device is Aborted, Fault or Paused. Normally it
will return in Paused state. If the user aborts then it will return in Aborted
state. If something goes wrong it will return in Fault state. If the user
disables then it will return in Disabled state. The state diagram subset below
shows the valid set of transitions:

.. uml::
    !include docs/stateMachineDefs.iuml

    state NormalStates {
        PreRun -down-> Pausing : Pause
        PreRun : Start state

        Running -down-> Pausing : Pause
        Running : Start state

        Pausing -right-> Paused

        Paused : End state
    }

    !include docs/stateMachineNotNormal.iuml

retrace(steps)
^^^^^^^^^^^^^^

This method will retrace a number of steps in the scan so that when it is
resumed it will overwrite invalid data that may have been acquired before
pause(). It will retrace by at least as many steps as demanded. It is allowed
from the Paused state and will block until the device is Paused again. Normally
it will return in Paused state. If the user aborts then it will return in
Aborted state. If something goes wrong it will return in Fault state. If the
user disables then it will return in a Disabled state. The state diagram subset
below shows the valid set of transitions:

.. uml::
    !include docs/stateMachineDefs.iuml

    state NormalStates {
        Paused -left-> Pausing : Rewind
        Paused : Start state
        Paused : End state

        Pausing -right-> Paused

        Ready -down-> Rewinding : Rewind
        Ready : Start state
        Ready : End state

        Rewinding -up-> Ready
    }

    !include docs/stateMachineNotNormal.iuml


resume()
^^^^^^^^

This method will resume a paused scan. It is allowed from the Paused state and
will block until the device is Running or in Fault state. Normally it will
return in Running state. If something goes wrong it will return in Fault state.
If the user disables then it will return in a Disabled state. The state diagram
subset below shows the valid set of transitions:

.. uml::
    !include docs/stateMachineDefs.iuml

    state NormalStates {
        Paused -right-> Resuming : Resume
        Paused : Start state

        Resuming -up-> Running
        Running : End state
    }

    !include docs/stateMachineNotNormal.iuml


abort()
^^^^^^^

This method will abort a configure or abandon the scan whether it is running or
paused. It is allowed from any normal block state, and will block until the
device is in a rest state. Normally it will return in Aborted state. If
something goes wrong it will return in Fault state.  If the used disables then
it will return in a Disabled state. The state diagram subset below shows the
valid set of transitions:

.. uml::
    !include docs/stateMachineDefs.iuml

    NormalStates : Start state
    NormalStates :
    NormalStates : Abort is allowed from
    NormalStates : any normal block state
    NormalStates --> Aborting : Abort

    Aborting -left-> Aborted
    Aborting -right-> Disabled : Disable
    Aborting -right-> Fault : Error

    state Aborted <<Abort>>
    Aborted : End state

    state Fault <<Fault>>
    Fault : End state

    state Disabled <<Disabled>>
    Disabled : End state

disable()
^^^^^^^^^

This method will stop the block responding to external input until reset() is
called. It is allowed from any state, and will make the device as Disabled and
return immediately. It will always return in Disabled state. The state diagram
subset below shows the valid set of transitions:

.. uml::
    !include docs/stateMachineDefs.iuml

    NormalStates : Start state
    NormalStates :
    NormalStates : Disable is allowed from
    NormalStates : any normal block state
    NormalStates --> Disabled : Disable

    state Disabled <<Disabled>>
    Disabled : End state


reset()
^^^^^^^

This method will reset the device into Idle state. It is allowed from Aborted,
Disabled, Ready or Fault states, and will block until the device is in a rest
state. Normally it will return in Idle state. If something goes wrong it will
return in Fault state. The state diagram subset below shows the valid set of
transitions:

.. uml::
    !include docs/stateMachineDefs.iuml

    state Ready <<Rest>>
    Ready -right-> Resetting : Reset
    Ready : Start state

    state Aborted <<Abort>>
    Aborted : Start state
    Aborted : End state
    Aborted --> Resetting : Reset

    state Fault <<Fault>>
    Fault : Start state
    Fault : End state
    Fault --> Resetting : Reset

    state Disabled <<Disabled>>
    Disabled : Start state
    Disabled : End state
    Disabled --> Resetting : Reset

    Resetting -down-> Idle
    Resetting -up-> Aborting : Abort
    Resetting -up-> Disabled : Disable
    Resetting -up-> Fault : Fault

    Aborting -left-> Aborted
    Aborting -right-> Fault : Error

    state Idle <<Rest>>
    Idle : End state


Messages and types
------------------

There are a number of client side verbs:

- Get: Get the structure of a Block or part of one
- Put: Put a value to an Attribute
- Post: Call a method of a Block
- Subscribe: Subscribe to changes in a Block or part of one
- Unsubscribe: Cancel one Subscribe

And a number of server side verbs:

- Error: Return an error to any one of the client side requests
- Value: Return a complete value to a subscription
- Changes: Return incremental changes to a subscription
- Return: Provide a return value to a Post, Get, Put, Unsubscribe, and indicate
  the cancellation of a Subscribe





Blocks and Parts
----------------

Blocks, Methods, and Attributes are what is exposed by Malcolm at run-time.
However, during the first iteration of Malcolm, it became apparent that
Python classes that implemented Blocks were too large and unweildy to easily
share code. Likewise, Attributes and Methods were too small, what is needed is
a collection of a small number of Attributes and Methods that form a coherent
reusable group. We will call these `Parts`. Blocks will be formed as a
composition of Parts, and to avoid repeating ourselves, we will define a
configuration language written in YAML.

A Block would be created by parsing a YAML file for initialisation Attributes,
taking values for those, and creating an object composed of the component parts.

To define initialisation attributes::

    init.String:
        name: prefix
        description: PV Prefix
        required: true

A group would look like this::

    gui.Group:
        name: configuration
        label: Configuration Parameters
        description: These will be used to configure the device
        collapse: true

For example, a repeated pattern is that of a PV Attribute, one that connects to
a readback PV (and optionally a demand PV) to allow::

    ca.Double:
        name: exposure
        description: Exposure time for each frame
        pv: {prefix}:Exposure
        rbv_suff: _RBV
        widget: textinput
        group: configuration

And an XML string sent over CA::

    ca.LongString:
        name: xml
        description: XML describing positions to tag NDArrays with
        pv: {prefix}:Filename
        widget: textarea
        group: configuration
        writeable: true

And an enumeration::

    ca.Enum:
        name: acquire
        description: Whether it is acquiring or not
        pv: {prefix}:Acquire
        labels:
            - Idle
            - Acquire
        widget: toggle
        writeable: true

All of these will call ca.create_pv(), monitor the resulting PV, and keep a
local attribute in sync with this value. If writeable, it will create a setter
on the attribute that does a caput callback on the PV, doing a get on the RBV
value to avoid the race condition on return.

Adding a statemachine is done with a Part::

    sm.RunnableDevice:

After this statement, we can add configuration methods for fixed values::

    methods.configure.imageMode:
        source: fixed
        value: Multiple
        phase: 1

And for values that should be passed straight through, with optional defaults::

    methods.configure.exposure:
        source: user
        value: 0.1
        phase: 2

For calculated values, we can create a custom Part that specifies the logic,
and instantiate it here::

    custom.PosPlugin.configure_xml:
        phase: 3

A key part of Malcolm is the nesting of Blocks. This means that we create lots
of composite Blocks that will control a number of child blocks and expose a
narrower interface to the end user. This means that they will take a number of
child objects at init::

    init.DetectorDriver:
        name: detectorDriver1
        description: DetectorDriver instance
        required: true

Some attributes will be a mirror of a child block attribute::

    attribute.Double:
        name: exposure
        source: detectorDriver1.exposure

Child block attributes can also be slaved from the internal attributes::

    slave.detectorDriver2.exposure:
        source: exposure

Child block attributes can also be fixed on reset of a block::

    fixed.detectorDriver2.period:
        value: 1.0

There will be a table view on this for the Load/Save view on Zebra2, that will
be used to generate the Parts above:

=============== ======= ======= ====================
Name            Value   Exposed Description
=============== ======= ======= ====================
DIV1.DIV        32
PCAP.ARM                Arm     Start the experiment
PCOMP1.START            Start   Start position
PCOMP2.START            Start
=============== ======= ======= ====================

Tables can be represented as repeated key value pairs::

    fixed.detectorDriver2.positions:
        value:
            - x: 32
              y: 45
            - x: 33
              y: 46


Threading Model
---------------

Generators
----------



