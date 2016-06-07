.. _structure:

Block Structure
===============

To describe how a Block is structured, we will use the `pvData Meta Language`_.
It is important to note that although many EPICS conventions are followed in
Malcolm, it is not a required part of it.

There are a number of operations that can be performed on the Block structure,
such as Get, Put, Subscribe, Post. These will be described in the
:ref:`messages` section. It is important to note that operations such as Get and
Subscribe will by default operate on the entire Block structure to avoid race
conditions between substructure updates, but some of the protocols supported
(like pvAccess) will allow the substructures to be operated on independantly.

Also note the placement of meta objects in the Block structure. The presence of
a meta element in the structure allows separation of the current value from the
metadata about the element. This is why there is no Method in the Block
structure, only a MethodMeta.

.. _pvData Meta Language:
    http://epics-pvdata.sourceforge.net/docbuild/pvDataJava/tip/documentation/
    pvDataJava.html#pvdata_meta_language

A Block looks like this::

    Block :=
        Attribute   state       // type=enum
        Attribute   status      // type=string
        Attribute   busy        // type=bool
        {Attribute  <attribute-name>}0+
        {MethodMeta <method-name>}0+
        BlockMeta   meta

    BlockMeta :=
        string      metaOf      // E.g. malcolm:zebra2/Zebra2:1.0
        string      description // Description of Block
        string[]    tags        // e.g. "instance:FlowGraph"

The `state` Attribute corresponds to the state described in the
:ref:`statemachine` section. The `status` Attribute will hold any status
message that is reported by the Block, for instance reporting on the progress
through a long running activity. The `busy` Attribute will be true if the state
is not a Rest state as described in the :ref:`statemachine` section. The tags
field of the Meta object is defined in the :ref:`tags` section.

An Attribute looks like this::

    Attribute := Scalar | ScalarArray | Table

    Scalar :=
        scalar_t    value
        alarm_t     alarm
        time_t      timeStamp
        ScalarMeta  meta

    ScalarArray :=
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
        string      description       // Description of attribute
        string      metaOf            // E.g. malcolm:core/UIntArray:1.0
        bool        writeable    :opt // True if you can Put at the moment
        string[]    tags         :opt // e.g. "widget:textinput"
        display_t   display      :opt // Display limits, units, etc, for numbers
        control_t   control      :opt // For writeable numbers
        string[]    oneOf        :opt // Allowed values if type is "Enum"
        string      label        :opt // Short label if different to name

    TableMeta :=
        string      description     // Description of attribute
        string      metaOf          // E.g. malcolm:core/Table:1.0
        structure   elements        // Metadata for each column, must have array
            {ScalarMeta <elname>}0+ // type
        string[]    tags       :opt // e.g. "widget:table"
        string[]    labels     :opt // List of column labels if different to
                                    // element names

ScalarMeta has a number of fields that will be present or not depending on the
contents of the type field. TableMeta contains a structure of elements that
describe the subelements that are allowed in the Table. The metaOf field
contains information about the type of the structure, which is explained in
more detail in the :ref:`types` section.

A MethodMeta looks like this::

    MethodMeta :=
        string      metaOf              // E.g. malcolm:core/Method:1.0    
        string      description         // Docstring
        MapMeta     takes               // Argument spec
        structure   defaults
            {any    <argname>}0+        // The defaults if not supplied
        MapMeta     returns        :opt // Return value spec if any
        bool        writeable      :opt // True if you can Post at the moment
        string[]    tags           :opt // e.g. "widget:confirmbutton"

    MapMeta :=
        string      metaOf              // E.g. malcolm:xspress3/Config:1.0
        structure   elements            // Metadata for each element in map
            {ScalarMeta | TableMeta <elname>}0+
        string[]    tags           :opt // e.g. "widget:group"
        string[]    required       :opt // These fields will always be present

The `takes` structure describes the arguments that should be passed to the
Method. The `returns` structure describes what will be returned as a result.
The `defaults` structure contains default values that will be used if the
argument is not supplied.

Methods are called by sending a Post message to the block with the name of the
method and the arguments described in the MethodMeta.


