Block Structure
===============

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
        string      metaOf      // E.g. malcolm:zebra2/Zebra2:1.0
        string      description // Description of Block
        string[]    tags        // e.g. "instance:FlowGraph"

The `state` Attribute corresponds to the state described in the
:ref:`statemachine` section. The `status` Attribute will hold any status
message that is reported by the Block, for instance reporting on the progress
through a long running activity. The `busy` Attribute will be true if the state
is not a Rest state as defined below.

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
        string      metaOf          // E.g. malcolm:core/UIntArray:1.0
        bool        writeable  :opt // True if you can Put
        string[]    tags       :opt // e.g. "widget:textinput"
        display_t   display    :opt // Display limits, units, etc, for numbers
        control_t   control    :opt // For writeable numbers
        string[]    oneOf      :opt // Allowed values if type is "enum"
        string      label      :opt // Short label if different to name

    TableMeta :=
        string      description     // Description of attribute
        string      metaOf          // E.g. malcolm:zebra2/SeqTable:1.0
        structure   elements        // Metadata for each column, must have array
            {ScalarMeta <elname>}0+ // type
        bool        writeable  :opt // True if you can Put
        string[]    tags       :opt // e.g. "widget:table"
        string[]    labels     :opt // List of column labels if different to
                                    // element names

ScalarMeta has a number of fields that will be present or not depending on the
contents of the type field. TableMeta contains a structure of elements that
describe the subelements that are allowed in the Table.

A Method looks like this::

    MapMeta :=
        string      metaOf              // E.g. malcolm:xspress3/Config:1.0
        structure   elements            // Metadata for each element in map
            {ScalarMeta | TableMeta <elname>}0+
        string[]    tags           :opt // e.g. "widget:group"
        string[]    required       :opt // These fields will always be present

    Method :=
        string      description         // Docstring
        MapMeta     takes               // Argument spec
        structure   defaults
            {any    <argname>}0+        // The defaults if not supplied
        MapMeta     returns        :opt // Return value spec if any
        string[]    valid_states   :opt // The only states method can be run in

The `takes` structure describes the arguments that should be passed to the
Method. The `returns` structure describes what will be returned as a result.
The `defaults` structure contains default values that will be used if the
argument is not supplied.

