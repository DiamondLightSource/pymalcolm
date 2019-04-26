.. _areadetector_tutorial:

AreaDetector Tutorial
=====================

You should already know how to create a `block_` in the `device_layer_` that
looks like a detector, and how to integrate it into a `scan_layer_` Block, using
a `DetectorChildPart`.  Now let's build a Detector Block to control an
`EPICS`_ `areaDetector`_ `simDetector`_ and its `plugin chain`_, and integrate
it into a scan.

Acquisition Strategy
--------------------

The application we have in mind is a multi-dimensional continuous scan, so we
want to be able to take a number of frames with the detector driver, calculate
some statistics on them, and write them in the same dimensionality as the scan
suggests into a `NeXus`_ formatted `HDF5`_ file. The driver and each plugin in
the chain will be represented by a Block in the `hardware_layer_`, and they will
all be controlled detector Block in the `device_layer_`. This is best viewed as
a diagram:

.. digraph:: simDetector_child_connections

    bgcolor=transparent
    compound=true
    node [fontname=Arial fontsize=10 shape=rect style=filled fillcolor="#8BC4E9"]
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
            detector_c [label="RunnableController"]
            DRV [label=<SimDetectorDriverPart<BR/>name: 'DRV'>]
            POS [label=<PositionLabellerPart<BR/>name: 'POS'>]
            STAT [label=<StatsPluginPart<BR/>name: 'STAT'>]
            HDF [label=<HDFWriterPart<BR/>name: 'HDF'>]
            DSET [label=<DatasetTablePart<BR/>name: 'DSET'>]
            detector_c -> DRV [style=invis]
            detector_c -> HDF [style=invis]
            DRV -> DSET [style=invis]
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

    There is a separation and hence an interface between `part_` and child
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
    the underlying plugins and presses Acquire. `EPICS`_ is responsible for
    writing data


Creating the Blocks
-------------------

So let's start with the Process definition
``./malcolm/modules/demo/DEMO-AREADETECTOR.yaml``:

.. literalinclude:: ../../malcolm/modules/demo/DEMO-AREADETECTOR.yaml
    :language: yaml

We have a couple more items to explain than in previous examples:

- The `builtin.defines.cmd_string` entry runs the shell command ``hostname -s``
  and makes it available inside this YAML file as ``$(hostname)``. This is
  needed because we are interfacing to an IOC that calculates the PV prefix
  based on the machine we are currently running on.

- The `builtin.defines.export_env_string` entries are so that we can export the
  EPICS server and repeater ports, again required as the IOC runs on these
  ports.

The other items are Blocks just like we encountered in previous tutorials.


Device Block
------------

The top level Device Block is a `sim_detector_runnable_block`. Let's take a look
at ``./malcolm/modules/ADSimDetector/blocks/sim_detector_runnable_block.yaml``
to see what one of those looks like:

.. literalinclude:: ../../malcolm/modules/ADSimDetector/blocks/sim_detector_runnable_block.yaml
    :language: yaml

The top of the file tells us what parameters should be passed, and defines a
docstring for the Block. After that we instantiate the `RunnableController`,
`sim_detector_driver_block` and its corresponding `DetectorDriverPart`, and
then a `stats_plugin_block` with is corresponding `StatsPluginPart`.


The entry after this is an `include_`. It lets us take some commonly used Blocks
and Parts and instantiate them at the level of the currently defined Block. If
we look at ``./malcolm/modules/ADCore/includes/filewriting_collection.yaml``
we'll see how it does this:

.. literalinclude:: ../../malcolm/modules/ADCore/includes/filewriting_collection.yaml
    :language: yaml

This will also instantiate the `DatasetTablePart`, `position_labeller_block` and
it corresponding `PositionLabellerPart`, and then `hdf_writer_block` with its
corresponding `HDFWriterPart`.

The reason we use an include file is so that other detectors can use this same
filewriting collection without having to copy and paste into the top level
object. There is some duplication in the parameter descriptions, but it ensures
that each YAML file is a self contained description of this level downwards.


Hardware Blocks
---------------

If we look at the next level down at something like
``./malcolm/modules/ADSimDetector/blocks/sim_detector_driver_block.yaml`` we
will see our PV interface:

.. literalinclude:: ../../malcolm/modules/ADSimDetector/blocks/sim_detector_driver_block.yaml
    :language: yaml

After the parameters, defines and `StatefulController` definition, most of our
CAPart objects are instantiated in
``./malcolm/modules/ADCore/includes/adbase_parts.yaml``. Let's look at the
start of that file:

.. literalinclude:: ../../malcolm/modules/ADCore/includes/adbase_parts.yaml
    :language: yaml
    :end-before: # For docs: before acquiring

This include structure mirrors that of the underlying templates, and allows us
to maintain a one to one mapping of YAML file to template file. If you look at
all of these CAParts you will see that they wrap up small numbers of PVs into
recognisable Attributes and Methods.

For instance:

.. literalinclude:: ../../malcolm/modules/ADCore/includes/adbase_parts.yaml
    :language: yaml
    :lines: 19-24

This corresponds to an `attribute_` that caputs to the ``NumImages`` pv with
callback when set, and uses ``NumImages_RBV`` as the current value.

Alternatively:

.. literalinclude:: ../../malcolm/modules/ADCore/includes/adbase_parts.yaml
    :language: yaml
    :lines: 25-31

This corresponds to a `method_` that caputs to the ``Acquire`` pv with callback,
and when it completes checks ``DetectorState_RBV`` to see if the detector
completed successfully or with an error.


Template Designs
----------------

One of the benefits of splitting the Hardware Layer from the Device Layer is
that we now get a useful interface that tells us what to load and save. We
tag all writeable CAParts as config Attributes by default, which will mean that
when we ``save()`` the Device Block, it will write the current value of all
these Attributes of all its child Hardware Blocks to a `design_` file.

We learned in the `motion_tutorial` that Designs are JSON formatted files stored
in the ``config_dir`` on ``save()``, and that they can be loaded by setting
the ``design`` Attribute at runtime. We now introduce the concept of a
`template_design_`. This is a read-only Design that is provided by Malcolm to
demonstrate how a Block might be used to implement a particular use case. It
always starts with the text ``template_``.

In our demo, we want our simDetector wired up in such a way that we can
implement the Acquisition Strategy set out earlier. The ``ADSimDetector``
module provides a design ``template_software_triggered`` that will do this for
us. We would discover this by running up Malcolm, and seeing the possible values
in the ``design`` drop-down list. If you are interested you can click
below to expand the text of
``blocks/sim_detector_runnable_block_designs/template_software_triggered.json``
in ``./malcolm/modules/ADSimDetector/`` to see what it will load:

.. container:: toggle

    .. container:: header

        Template Design JSON: template_software_triggered

    .. literalinclude:: ../../malcolm/modules/ADSimDetector/blocks/sim_detector_runnable_block_designs/template_software_triggered.json
        :language: json

This Design will setup the plugin chain correctly for areaDetector to work the
way that Malcolm expects. In particular it makes sure that the plugins are in
the correct way that the HDF writer gets the tags it expects on each NDArray
that it receives.

.. note::

    The reason that this rewiring is done in the Design file rather than each
    plugin Part is that it allows extra plugins to be placed inline that Malcolm
    doesn't and shouldn't have to know about.

Scan Blocks can have saved `design_` files just like Device Blocks. The
difference is that they have far fewer entries as their children typically save
their config in their own Design files. If we look at
``./malcolm/modules/demo/blocks/scan_2det_block_designs/template_both_detectors.json``
we will see just how few entries there are:

.. literalinclude:: ../../malcolm/modules/demo/blocks/scan_2det_block_designs/template_both_detectors.json
    :language: json

Basically we imagine that each Device Block will have a number of designs for
hardware or software triggering or different motor setups, and the Scan Block
will say "I need DET with the hardware_trigger design and MOTORS with
hkl_geometry". The Scan Block will not load its children's designs at init, but
will set them before every ``configure()`` call, ensuring the Device Blocks are
all setup correctly at the beginning of every scan.

Now we know what we need to load, we need to work out when to load it. There is
an ``initial_design`` parameter that we pass to any `ManagerController` or
`RunnableController` that will tell it what design to load when Malcolm starts
up, and we have two places we could load an `initial_design_`:

1.  In the detector. In this case, the design will be loaded as soon as Malcolm
    starts, but if there is not a clear single design that all scans use then
    it is not clear what to set it to.

2.  In the scan. In this case, the design will be loaded at the beginning of
    every scan. This means that scans can use different designs for their
    children, and Devices are guaranteed to be in the right state even if
    another application changes PVs between scans.

.. caution::

    If you set ``initial_design`` on a Block in the ``device_layer``, then PVs
    will change when you restart Malcolm. This may or may not be what you want.

We will choose case 2 here and set the scan Block to load
``template_both_detectors`` before each scan. It is worth pointing out that we
are only likely to set ``initial_design`` once a scan is working. Once a design
is set, it will be restored every ``configure()``, so a ``save()`` or unsetting
the design is required to keep any manual changes to child Blocks.

Running a Scan
--------------

First you need an areaDetector IOC. From the Diamond launcher, select
``Utilities -> GDA AreaDetector Simulation``, then click the ``Start IOC``
button.

Let's start up the example and see it in action::

    [me@mypc pymalcolm]$ ./malcolm/imalcolm.py malcolm/modules/demo/DEMO-AREADETECTOR.yaml
    Loading...
    Python 2.7.13 (default, Oct  3 2017, 11:17:53)
    Type "copyright", "credits" or "license" for more information.

    IPython 5.4.1 -- An enhanced Interactive Python.
    ?         -> Introduction and overview of IPython's features.
    %quickref -> Quick reference.
    help      -> Python's own help system.
    object?   -> Details about 'object', use 'object??' for extra details.


    Welcome to iMalcolm.

    self.mri_list:
        ['mypc-ML-MOT-01:COUNTERX', 'mypc-ML-MOT-01:COUNTERY', 'mypc-ML-MOT-01', 'mypc-ML-DET-01', 'mypc-ML-DET-02:DRV', 'mypc-ML-DET-02:STAT', 'mypc-ML-DET-02:POS', 'mypc-ML-DET-02:HDF5', 'mypc-ML-DET-02', 'mypc-ML-SCAN-01', 'WEB', 'PVA']

    # To create a view of an existing Block
    block = self.block_view("<mri>")

    # To create a proxy of a Block in another Malcolm
    self.make_proxy("<client_comms_mri>", "<mri>")
    block = self.block_view("<mri>")

    # To view state of Blocks in a GUI
    !firefox localhost:8008

    In [1]:

This time we will configure from the commandline. You may have some of these
lines in your history from earlier tutorials. Note you will need to replace
'mypc' with the name of your pc::

    In [1]: from scanpointgenerator import LineGenerator, CompoundGenerator

    In [2]: scan = self.block_view("mypc-ML-SCAN-01")

    In [3]: yline = LineGenerator("y", "mm", -1, 0, 6)

    In [4]: xline = LineGenerator("x", "mm", 4, 5, 5, alternate=True)

    In [5]: generator = CompoundGenerator([yline, xline], [], [], duration=0.5)

    In [6]: scan.configure(generator, "/tmp")


After configure, the detector will also report the datasets that it is about
to write in the ``datasets`` Attribute::

    In [7]: from annotypes import json_encode

    In [8]: print(json_encode(scan.datasets.value, indent=4))
    {
        "typeid": "malcolm:core/Table:1.0",
        "name": [
            "INTERFERENCE.data",
            "INTERFERENCE.sum",
            "RAMP.data",
            "RAMP.sum",
            "y.value_set",
            "x.value_set"
        ],
        "filename": [
            "INTERFERENCE.h5",
            "INTERFERENCE.h5",
            "RAMP.h5",
            "RAMP.h5",
            "RAMP.h5",
            "RAMP.h5"
        ],
        "type": [
            "primary",
            "secondary",
            "primary",
            "secondary",
            "position_set",
            "position_set"
        ],
        "rank": [
            4,
            4,
            4,
            4,
            1,
            1
        ],
        "path": [
            "/entry/data",
            "/entry/sum",
            "/entry/detector/detector",
            "/entry/sum/sum",
            "/entry/detector/y_set",
            "/entry/detector/x_set"
        ],
        "uniqueid": [
            "/entry/uid",
            "/entry/uid",
            "/entry/NDAttributes/NDArrayUniqueId",
            "/entry/NDAttributes/NDArrayUniqueId",
            "",
            ""
        ]
    }

This is very similar to the `scanning_tutorial`, but now datasets are reported
from both detectors. We also have a couple of datasets with type position_set,
these are the demand positions for the ``x`` and ``y`` axes that take their
setpoints from the generator values.

Now that you have the files open, you can use the `h5watch`_ command to monitor
the dataset and see it grow::

    [me@mypc pymalcolm]$ h5watch /tmp/INTERFERENCE.h5/entry/uid
    Opened "/tmp/INTERFERENCE.h5" with sec2 driver.
    Monitoring dataset /entry/uid...

You will be able to run a the same h5watch command on
``/tmp/RAMP.h5/entry/NDAttributes/NDArrayUniqueId`` to see the areaDetector
dataset grow, but only when the scan has started as the HDF writer can't write
the datasets until it knows the size of the first detector frame.

You can open the web GUI again to inspect the state of the various objects,
and you will see that both the ``RAMP`` and ``INTERFERENCE`` detector objects
are in state ``Armed``, as is the ``SCAN``. You can then run a scan, either from
the web GUI, or the commandline, resetting when it is done to close the file
(only needed so that the commandline tools will work)::

    In [9]: scan.run()

    In [10]: scan.reset()

This will write 30 frames of data to ``/tmp/INTERFERENCE.h5`` directly, and
supervise the writing of 30 frames of data to ``/tmp/RAMP.h5`` via areaDetector.
You can take a look at the `HDF5`_ files to see what has been written::

    [me@mypc pymalcolm]$ module load hdf5/1-10-4
    [me@mypc pymalcolm]$ h5dump -n /tmp/RAMP.h5
    HDF5 "/tmp/RAMP.h5" {
    FILE_CONTENTS {
     group      /
     group      /entry
     group      /entry/NDAttributes
     dataset    /entry/NDAttributes/ColorMode
     dataset    /entry/NDAttributes/NDArrayEpicsTSSec
     dataset    /entry/NDAttributes/NDArrayEpicsTSnSec
     dataset    /entry/NDAttributes/NDArrayTimeStamp
     dataset    /entry/NDAttributes/NDArrayUniqueId
     dataset    /entry/NDAttributes/d0
     dataset    /entry/NDAttributes/d1
     dataset    /entry/NDAttributes/timestamp
     group      /entry/detector
     dataset    /entry/detector/detector
     dataset    /entry/detector/x_set
     dataset    /entry/detector/y_set
     group      /entry/sum
     dataset    /entry/sum/sum
     dataset    /entry/sum/x_set -> /entry/detector/x_set
     dataset    /entry/sum/y_set -> /entry/detector/y_set
     }
    }

This corresponds to the dataset table that the Block reported before run() was
called. You can examine the uniqueid dataset to see the order that the frames
were written::

    [me@mypc pymalcolm]$ h5dump -d /entry/NDAttributes/NDArrayUniqueId /tmp/RAMP.h5
    HDF5 "/tmp/RAMP.h5" {
    DATASET "/entry/NDAttributes/NDArrayUniqueId" {
       DATATYPE  H5T_STD_I32LE
       DATASPACE  SIMPLE { ( 6, 5, 1, 1 ) / ( H5S_UNLIMITED, H5S_UNLIMITED, 1, 1 ) }
       DATA {
       (0,0,0,0): 1,
       (0,1,0,0): 2,
       (0,2,0,0): 3,
       (0,3,0,0): 4,
       (0,4,0,0): 5,
       (1,0,0,0): 10,
       (1,1,0,0): 9,
       (1,2,0,0): 8,
       (1,3,0,0): 7,
       (1,4,0,0): 6,
       (2,0,0,0): 11,
       (2,1,0,0): 12,
       (2,2,0,0): 13,
       (2,3,0,0): 14,
       (2,4,0,0): 15,
       (3,0,0,0): 20,
       (3,1,0,0): 19,
       (3,2,0,0): 18,
       (3,3,0,0): 17,
       (3,4,0,0): 16,
       (4,0,0,0): 21,
       (4,1,0,0): 22,
       (4,2,0,0): 23,
       (4,3,0,0): 24,
       (4,4,0,0): 25,
       (5,0,0,0): 30,
       (5,1,0,0): 29,
       (5,2,0,0): 28,
       (5,3,0,0): 27,
       (5,4,0,0): 26
       }
       ...

This tells us that it was written in a snake fashion, with the first row
written 1-5 left-to-right, the second row 6-10 right-to-left, etc. The detector
will always increment the uniqueid number when it writes a new frame, so if
you try pausing and setting the Completed Steps Attribute, you will see the
uniqueID number jump where you overwrite existing frames with new frames with a
greater uniqueID. This will mean that the two detectors will have matching
unique ID datasets.

Conclusion
----------

This tutorial has given us an understanding of how `areaDetector`_ plugin
chains can be controlled in Malcolm, and how multiple detectors interface into
a scan and can be paused and rewound together. The next tutorial will focus
on using real hardware to perform a continuous scan.

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

.. _h5watch:
    https://support.hdfgroup.org/HDF5/doc/RM/Tools/h5watch.htm
