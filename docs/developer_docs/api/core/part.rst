Part
----

A Part contains the logic for a Controller to interact with a child Block to
perform more device-specific actions:

.. module:: malcolm.core

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

