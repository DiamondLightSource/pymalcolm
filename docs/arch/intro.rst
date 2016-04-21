Introduction
============

Malcolm can be considered to be a distributed object system. This document will
use a number of terms to identify key components of Malcolm

Terms for Malcolm users
-----------------------

Users of Malcolm need to know what the following terms mean:

- Process: A Malcolm instance containing a number of Blocks along with various
  communication modules to communicate with other Malcolm instances. A Process
  can be a client of or a server to a number of other Processes.

- Block: An object consisting of a number of Attributes and Methods. It should
  be designed to be as small and self contained as possible, and complex logic
  should be implemented by nesting Blocks. For example, a detector driver would
  be a Block, as would an HDF writer, but there would also be a higher level
  detector Block to co-ordinate the low level Blocks. Any Block may be
  synchronized among a number of Processes, the Block acting as the server will
  perform the logic, and the client copies will expose the same API as the
  server Block to the end user.

- Attributes: Hold the current value of a piece of data of a fixed simple type
  like Int, Float, String, Enum, IntArray, Table or a named Map. You can Get
  and Subscribe to changes in all Attributes, and Put to Attributes with a
  defined setter. In a client Block, Attributes will mirror the value of the
  Block acting as a server, with a Put operation being forwarded to the server
  Block. For example, the State of a Block would be an Attribute, as would the
  CurrentStep of a scan.

- Methods: Expose a function call. You can Call a Method with a (possibly empty)
  Map of arguments, and it will return a (possibly empty) Map of return values.
  In a client Block, the Call will be forwarded to the server Block, and the
  return value returned to the caller. For example, configure() and run() would
  be Methods of a Blocks used in a mapping scan.

For example, in the following diagram, Process1 is hosting two Blocks, and
Process2 has a client of Block 2 as a local object:

.. uml::
    !include docs/style.iuml

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

Terms for Malcolm developers
----------------------------

Developers of Malcolm are also required to know about some additional terms
that are used in creating Blocks:

- State Machine: Every Malcolm Block contains a State Machine that maps the
  allowed transitions between different values of the State Attribute. This
  allows external applications to monitor what a Block is doing, and gives a
  condition for whether particular Methods can run or not. See the
  :ref:`statemachine` section for examples.

- Controller: A State Machine just exposes the list of allowed transitions
  between States. The Controller provides the logic that goes behind those
  transitions. It creates a number of Methods fixing the external interface of
  how to control the blocks, creates some Attributes for monitoring
  configuration and runtime variables, and then exposes a number of hooks that
  Parts can utilise to be executed and control transition to other states. For
  example, there will be an AreaDetectorController with hooks for
  PreRunDriverStart, PreRunPluginStart, and Running.

- Parts: These provide the logic for using a particular child Block with a
  particular Controller. It can register to use a number of hooks that the
  Controller provides, and the Controller will wait for all using that hook to
  run concurrently before moving to the next State. Parts can also create
  Attributes on the parent Block, as well as contribute Attributes that should
  be taken as arguments to Methods provided by the Controller. For example,
  there will be an HDFWriterPart that knows how to set PVs on the HDFWriter in
  the right order and expose the FilePath as an Attribute to the configure()
  method.

In the following diagram, the DetectorBlock is made up of an
AreaDetectorController and 3 Parts:

- MirrorPart: Exposes an Attribute of the underlying DetectorDriverBlock as an
  Attribute on the DetectorBlock and argument to configure()

- DriverRunPart: During the PreRunDriverStart hook of the
  AreaDetectorController, starts the DetectorDriverBlock running and in the
  Running hook waits until it's finished

- HDFWriterPart: Exposes FilePath as an argument to configure() and during the
  PreRunPluginStart, starts the HDFWriterBlock running and waits until it has
  started.

.. uml::
    !include docs/style.iuml
    [DetectorDriverBlock]
    [HDFWriterBlock]

    frame DetectorBlock {
        [AreaDetectorController]
        [MirrorPart] .up.> [AreaDetectorController] : Hooks into
        [DriverRunPart] .up.> [AreaDetectorController] : Hooks into
        [HDFWriterPart] .up.> [AreaDetectorController] : Hooks into
        [MirrorPart] -down-> [DetectorDriverBlock] : Controls
        [DriverRunPart] -down-> [DetectorDriverBlock] : Controls
        [HDFWriterPart] -down-> [HDFWriterBlock] : Controls
    }

The Controllers and child Blocks are generic, the Parts can be generic but are
usually application specific. By forming the blocks by composition, shared
behaviour can be isolated into Parts that can easily be reused.
