malcolm.core
============

This is the core of Malcolm

.. automodule:: malcolm.core
    :members:

.. autoclass:: Alarm
    :members:

.. autoclass:: AlarmSeverity
    :members:

.. autoclass:: AlarmStatus
    :members:

.. autoclass:: AttributeModel
    :members:

    An Attribute holds a value such as an Int, Float or Enum Table representing
    the current state of a block.

    Hold the current value of a piece of data of a fixed simple type
    like Int, Float, String, Enum, IntArray or Table. You can Get and Subscribe to
    changes in all Attributes, and Put to Attributes with a defined setter. In a
    client Block, Attributes will mirror the value of the Block acting as a
    server, with a Put operation being forwarded to the server Block. For example,
    the State of a Block would be an Attribute, as would the CurrentStep of a
    scan.

    Subclasses serialize differently.

.. autoclass:: Attribute
    :members:

    An Attribute holds a value such as an Int, Float or Enum Table representing
    the current state of a block.

    Hold the current value of a piece of data of a fixed simple type
    like Int, Float, String, Enum, IntArray or Table. You can Get and Subscribe to
    changes in all Attributes, and Put to Attributes with a defined setter. In a
    client Block, Attributes will mirror the value of the Block acting as a
    server, with a Put operation being forwarded to the server Block. For example,
    the State of a Block would be an Attribute, as would the CurrentStep of a
    scan.

    Subclasses serialize differently.

.. autoclass:: BlockMeta
    :members:

.. autoclass:: Block
    :members:

    An object consisting of a number of Attributes and Methods.



    It should
    be designed to be as small and self contained as possible, and complex logic
    should be implemented by nesting Blocks. For example, a detector driver would
    be a Block, as would an HDF writer, but there would also be a higher level
    detector Block to co-ordinate the low level Blocks. Any Block may be
    synchronized among a number of Processes, the Block acting as the server will
    perform the logic, and the client copies will expose the same API as the
    server Block to the end user.

.. autoclass:: Context
    :members:

.. autoclass:: Controller
    :members:

    Controller: A State Machine just exposes the list of allowed transitions
    between StatefulStates. The Controller provides the logic that goes behind those
    transitions. It creates a number of Methods fixing the external interface of
    how to control the blocks, creates some Attributes for monitoring
    configuration and runtime variables, and then exposes a number of hooks that
    Parts can utilise to be executed and control transition to other states. For
    example, there will be an AreaDetectorController with hooks for
    PreRunDriverStart, PreRunPluginStart, and Running.

    A Controller implements the logic for changing states and contains Hooks for
    allow Parts to run any functions that are relevant to the current transition

.. autoexception:: TimeoutError

.. autoexception:: AbortedError

.. autoexception:: ResponseError

.. autoexception:: UnexpectedError

.. autoexception:: BadValueError

.. autoclass:: Future
    :members:

.. autoclass:: Hook
    :members:

    Hooks are used to link a Parts' Methods to the relevant state transition of
    the controller:

.. autoclass:: Info
    :members:

    Infos are used to report things from Hook runs

.. autoclass:: Loggable
    :members:

.. autoclass:: MapMeta
    :members:

.. autoclass:: Map
    :members:

.. autoclass:: Meta
    :members:

.. autoclass:: MethodModel
    :members:

    A Method exposes a function call for a Block:

    Expose a function call. You can Call a Method with a (possibly empty)
    Map of arguments, and it will return a (possibly empty) Map of return values.
    In a client Block, the Call will be forwarded to the server Block, and the
    return value returned to the caller. For example, configure() and run() would
    be Methods of a Blocks used in a mapping scan.

.. data:: REQUIRED

    Used to mark an argument in method_takes() or method_returns() as required

.. data:: OPTIONAL

    Used to mark an argument in method_takes() or method_returns() as optional

.. autofunction:: method_takes

.. autofunction:: method_returns

.. autoclass:: Method
    :members:

    A Method exposes a function call for a Block:

    Expose a function call. You can Call a Method with a (possibly empty)
    Map of arguments, and it will return a (possibly empty) Map of return values.
    In a client Block, the Call will be forwarded to the server Block, and the
    return value returned to the caller. For example, configure() and run() would
    be Methods of a Blocks used in a mapping scan.

.. autoclass:: Part
    :members:

    These provide the logic for using a particular child Block with a
    particular Controller. It can register to use a number of hooks that the
    Controller provides, and the Controller will wait for all using that hook to
    run concurrently before moving to the next State. Parts can also create
    Attributes on the parent Block, as well as contribute Attributes that should
    be taken as arguments to Methods provided by the Controller. For example,
    there will be an HDFWriterPart that knows how to set PVs on the HDFWriter in
    the right order and expose the FilePath as an Attribute to the configure()
    method.

    A Part contains the logic for a Controller to interact with a child Block to
    perform more device-specific actions:


.. autoclass:: Process
    :members:

    A Malcolm instance containing a number of Blocks along with various
    communication modules to communicate with other Malcolm instances. A Process
    can be a client of or a server to a number of other Processes.

    A Process is a host for Block instances and allows communication between them:



.. autoclass:: Request
    :members:

    Request objects are used to interact with another block:

.. autoclass:: Get
    :members:

.. autoclass:: Put
    :members:

.. autoclass:: Post
    :members:

.. autoclass:: Subscribe
    :members:

.. autoclass:: Unsubscribe
    :members:


.. autoclass:: Response
    :members:

    Response objects are received when a requested action is complete:

.. autoclass:: Return
    :members:

.. autoclass:: Error
    :members:

.. autoclass:: Update
    :members:

.. autoclass:: Delta
    :members:


.. autoclass:: Serializable
    :members:

    Objects that need to be sent over json implement the Serializable class:

.. autoclass:: Spawned
    :members:


.. autoclass:: StringArray
    :members:

.. autoclass:: Table
    :members:

.. autoclass:: TimeStamp
    :members:

.. autoclass:: VArrayMeta
    :members:

.. autoclass:: VMeta
    :members: