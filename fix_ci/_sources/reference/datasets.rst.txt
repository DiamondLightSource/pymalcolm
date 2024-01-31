.. _datasets:

Datasets and Detectors
======================
A scan typically includes at least one detector.

Detectors are defined as devices that produce data. The data produced by
a detector is described by a table of Datasets. Each Dataset typically describes
a path within an HDF file.

Most scans include at least one detector block in the device layer and that
block must include a `DatasetTablePart`. This part adds a ``datasets``
attribute to the block which allows clients to determine the location and
shape of the data being produced by the detector.

Every part that produces data must return from configure() an `Infos <info_>`
of type `DatasetProducedInfo` for each dataset it will produce.

The DataSetTablePart collects these Infos and publishes them in the
``datasets`` Attribute.

Dataset tables should be NeXus compatible and as such would contain
a ``primary`` set, any number of
``secondary`` and ``monitor`` sets plus a ``position_set`` for each dimension
of the scan. It would also contain a ``position_value`` for each dimension
if axis read-backs are available. The definitions of these types
are provided by `DatasetType` as follows:

.. automodule:: malcolm.modules.scanning.util
    :members: DatasetType
    :noindex:


