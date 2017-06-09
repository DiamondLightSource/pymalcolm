.. _areadetector_tutorial:

AreaDetector Tutorial
=====================

You should already know how to create a `block_` in the `device_layer` using a
`RunnableController` and some `Part` subclasses to control low level Blocks in
the `hardware_layer`. Now let's build this same kind of structure to control an
`EPICS`_ `areaDetector`_ `simDetector`_ and its `plugin chain`_.

Acquisition Strategy
--------------------

The application we have in mind is a multi-dimensional continuous scan, so we
want to be able to take a number of frames with the detector driver, calculate
some statistics on them, and write them in the same dimensionality as the scan
suggests into a `NeXus`_ formatted `HDF5`_ file. The driver and each plugin in
the chain will be represented by a Block in the `hardware_layer`, and they will
all be controlled detector Block in the `device_layer`. This is best viewed as a
diagram:

.. digraph:: simDetector_child_connections

    bgcolor=transparent
    compound=true
    node [fontname=Arial fontsize=10 shape=Mrecord style=filled fillcolor="#8BC4E9"]
    graph [fontname=Arial fontsize=10]
    edge [fontname=Arial fontsize=10 arrowhead=vee]

    subgraph cluster_device {
        label="Device Layer"
		style=filled
		color=lightgrey

        subgraph cluster_detector {
            label="DETECTOR"
            ranksep=0.1
		    color=white
            ticker_c [label="RunnableController"]
            DRV [label="{SimDetectorDriverPart|name: 'DRV'}"]
            POS [label="{PositionLabellerPart|name: 'POS'}"]
            STAT [label="{StatsPluginPart|name: 'STAT'}"]
            HDF [label="{HDFWriterPart|name: 'HDF'}"]
            ticker_c -> DRV [style=invis]
            ticker_c -> POS [style=invis]
            ticker_c -> STAT [style=invis]
            ticker_c -> HDF [style=invis]
            {rank=same; DRV -> POS -> STAT -> HDF}
        }
    }

    subgraph cluster_hardware {
        label="Hardware Layer"
		style=filled
		color=lightgrey

        subgraph cluster_drv {
            label="DETECTOR:DRV"
            color=white
            drv_c [label="StatefulController"]
            drv_p [label="CAParts"]
            drv_c -> drv_p [style=invis]
        }

        subgraph cluster_pos {
            label="DETECTOR:POS"
            color=white
            pos_c [label="StatefulController"]
            pos_p [label="CAParts"]
            pos_c -> pos_p [style=invis]
        }

        subgraph cluster_stat {
            label="DETECTOR:STAT"
            color=white
            stat_c [label="StatefulController"]
            stat_p [label="CAParts"]
            stat_c -> stat_p [style=invis]
        }

        subgraph cluster_hdf {
            label="DETECTOR:HDF"
            color=white
            hdf_c [label="StatefulController"]
            hdf_p [label="CAParts"]
            hdf_c -> hdf_p [style=invis]
        }
    }

    DRV -> drv_c [lhead=cluster_drv minlen=3 style=dashed]
    POS -> pos_c [lhead=cluster_pos minlen=3 style=dashed]
    STAT -> stat_c [lhead=cluster_stat minlen=3 style=dashed]
    HDF -> hdf_c [lhead=cluster_hdf minlen=3 style=dashed]

.. note::

    There is a separation and hence and interface between `part_` and child
    `block_`. The interface goes in the child Block, and the logic goes in the
    controlling Part. This is desirable because we could potentially have many
    possible logic Parts that could control the same kind of child Block, and
    making this split keeps the Parts small and more readable.

Each Hardware Block is responsible for controlling a group of `PVs`_ that make
up a single plugin or driver:

- The DRV Block corresponds to the `simDetector`_ driver, which is responsible
  for producing the right number of `NDArrays`_, each tagged with a unique ID.

- The POS Block corresponds to the `NDPosPlugin`_ plugin which tags each NDArray
  with a number of attributes that can be used to determine its position within
  the dataset dimensions.

- The STAT Block corresponds to the `NDPluginStats`_ plugin which tags each
  NDArray with a number of statistics that can be calculated from the data.

- The HDF Block corresponds to the `NDFileHDF5`_ plugin which writes NDArrays
  into an HDF file, getting the position within the dataset dimensions from an
  attribute attached to the NDArray.

The detector Device Block contains 4 Parts, one for each Hardware Block, that
are responsible for setting `Attributes <attribute_>` on the relevant child
Block in the right order. The Controller is responsible for calling each of its
Parts `Hooked <hook_>` methods in the right order.

.. note::

    Malcolm's role in this application is purely supervisory, it just sets up
    the underlying plugins and presses Go. `EPICS`_ is responsible for writing
    data

Creating the Blocks
-------------------

YAML file


Hardware Blocks
---------------

CAParts

Device Block
------------

Parts

Running a Scan
--------------

Demo


Conclusion
----------

This tutorial has given us






.. _simDetector:
    http://cars.uchicago.edu/software/epics/simDetectorDoc.html

.. _plugin chain:
    http://cars.uchicago.edu/software/epics/pluginDoc.html

.. _NDArrays:
    http://cars.uchicago.edu/software/epics/areaDetectorDoc.html#NDArray

.. _NDPosPlugin:
    http://cars.uchicago.edu/software/epics/NDPosPlugin.html

.. _NDPluginStats:
    http://cars.uchicago.edu/software/epics/NDPluginStats.html

.. _NDFileHDF5:
    http://cars.uchicago.edu/software/epics/NDFileHDF5.html