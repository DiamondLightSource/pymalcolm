.. _structure:

Block Structure
===============

To describe how a Block is structured, we will use the `pvData Meta Language`_.
It is important to note that although many EPICS conventions are followed in
Malcolm, it is not a required part of it. The typeid of structures (in italics)
will appear as a string typeid field in JSON serialized messages, and as the
typeid in pvData serialized messages.

There are a number of operations that can be performed on the Block structure,
such as Get, Put, Subscribe, Post. These will be described in the
`messages` section. It is important to note that operations such as Get and
Subscribe will by default operate on the entire Block structure to avoid race
conditions between substructure updates, but some of the protocols supported
(like pvAccess) will allow the substructures to be operated on independently.

Also note the placement of meta objects in the Block structure. The presence of
a meta element in the structure allows separation of the current value from the
metadata about the element.

.. _pvData Meta Language:
    http://epics-pvdata.sourceforge.net/docbuild/pvDataJava/tip/documentation/
    pvDataJava.html#pvdata_meta_language

A Block looks like this::

    Block :=

    malcolm:core/Block:1.0
        BlockMeta   meta
        Attribute   state       // ChoiceMeta
        Attribute   status      // StringMeta
        Attribute   busy        // BooleanMeta
        {Attribute  <attribute-name>}0+
        {Method <method-name>}0+


    BlockMeta :=

    malcolm:core/BlockMeta:1.0
        string      description // Description of Block
        string[]    tags  :opt  // e.g. "instance:FlowGraph"

The `state` Attribute corresponds to the state described in the
:ref:`statemachine` section. The `status` Attribute will hold any status
message that is reported by the Block, for instance reporting on the progress
through a long running activity. The `busy` Attribute will be true if the state
is not a Rest state as described in the :ref:`statemachine` section. The tags
field of the Meta object is defined in the :ref:`tags` section.

An Attribute looks like this::

    Attribute := Scalar | ScalarArray | Table | PointGenerator


    NTScalar :=

    epics:nt/NTScalar:1.0 // Conformant but optional fields -> meta
        scalar_t    value
        alarm_t     alarm       :opt
        time_t      timeStamp   :opt
        ScalarMeta  meta        :opt


    ScalarArray :=

    epics:nt/NTScalarArray:1.0 // Conformant but optional fields -> meta
        scalar_t[]      value
        alarm_t         alarm       :opt
        time_t          timeStamp   :opt
        ScalarArrayMeta meta        :opt


    Table :=

    malcolm:core/NTTable:1.0 // Conformant but optional fields -> meta
        string[]    labels
        TableValue  value
        alarm_t     alarm       :opt
        time_t      timeStamp   :opt
        TableMeta   meta        :opt


    TableValue :=

    structure
        {scalar_t[] <colname>}0+


    PointGenerator :=

    malcolm:core/PointGenerator:1.0
        PointGeneratorValue value
        alarm_t             alarm       :opt
        time_t              timeStamp   :opt
        PointGeneratorMeta  meta        :opt


The structures are very similar, and all hold the current value in whatever
type is appropriate for the Attribute. Each structure contains a `meta` field
that describes the values that are allowed to be passed to the value field of
the structure::

    ScalarMeta := BooleanMeta | StringMeta | ChoiceMeta | NumberMeta


    BooleanMeta :=

    malcolm:core/BooleanMeta:1.0
        string      description     // Description of attribute
        string[]    tags       :opt // e.g. "widget:led"
        bool        writeable  :opt // True if you can Put at the moment
        string      label      :opt // Short label if different to name


    StringMeta :=

    malcolm:core/StringMeta:1.0
        string      description     // Description of attribute
        string[]    tags       :opt // e.g. "widget:textinput"
        bool        writeable  :opt // True if you can Put at the moment
        string      label      :opt // Short label if different to name


    ChoiceMeta :=

    malcolm:core/ChoiceMeta:1.0
        string[]    choices         // Value will be one of these
        string      description     // Description of attribute
        string[]    tags       :opt // e.g. "widget:combo"
        bool        writeable  :opt // True if you can Put at the moment
        string      label      :opt // Short label if different to name


    NumberMeta :=

    malcolm:core/NumberMeta:1.0
        string      dtype           // e.g. int8, uint32, float64
        string      description     // Description of attribute
        string[]    tags       :opt // e.g. "widget:textupdate"
        bool        writeable  :opt // True if you can Put at the moment
        string      label      :opt // Short label if different to name
        display_t   display    :opt // Display limits, units, etc
        control_t   control    :opt // Control limits for writeable numbers

The ScalarArrayMeta structures are identical to the ScalarMeta structures, but
have "Array" in their typeid. TableMeta has similar fields::


    TableMeta :=

    malcolm:core/TableMeta:1.0
        structure   elements        // Metadata for each column
            {ScalarArrayMeta <elname>}0+
        string      description     // Description of attribute
        string[]    tags       :opt // e.g. "widget:table"
        bool        writeable  :opt // True if you can Put at the moment
        string      label      :opt // Short label if different to name

It contains a structure of elements that describe the subelements that are
allowed in the Table.

A PointGeneratorMeta looks similar::

    PointGeneratorMeta :=

    malcolm:core/PointGeneratorMeta:1.0
        string      description     // Description of attribute
        string[]    tags       :opt // e.g. "widget:generatorpicker"
        bool        writeable  :opt // True if you can Put at the moment
        string      label      :opt // Short label if different to name


A Method looks like this::

    Argument := scalar_t | scalar_t[] | TableValue | PointGeneratorValue

    Method :=

    malcolm:core/Method:1.0
        MapMeta     takes           // Argument spec
        structure   defaults
            {Argument   <argname>}0+    // The defaults if not supplied
        string      description     // Docstring
        string[]    tags       :opt // e.g. "widget:confirmbutton"
        bool        writeable  :opt // True if you can Post at the moment
        string      label      :opt // Short label if different to name
        MapMeta     returns    :opt // Return value spec if any


    ArgumentMeta := ScalarMeta | ScalarArrayMeta | TableMeta |
        PointGeneratorMeta

    MapMeta :=

    malcolm:core/MapMeta:1.0
        structure   elements            // Metadata for each element in map
            {ArgumentMeta <elname>}0+
        string      description         // Description of what the map is for
        string[]    tags           :opt // e.g. "widget:group"
        string[]    required       :opt // These fields will always be present

The `takes` structure describes the arguments that should be passed to the
Method. The `returns` structure describes what will be returned as a result.
The `defaults` structure contains default values that will be used if the
argument is not supplied.

Methods are called by sending a Post message to the block with the name of the
method and the arguments described in the takes MapMeta.

The Map just looks like this::

    Map :=

    structure
        {Arguemnt   <argname>}0+

    

