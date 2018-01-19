.. _areadetector_tutorial:

AreaDetector Tutorial
=====================

You should already know how to create a `block_` in the `device_layer_` using a
`RunnableController` and some `Part` subclasses to control low level Blocks in
the `hardware_layer_`. Now let's build this same kind of structure to control an
`EPICS`_ `areaDetector`_ `simDetector`_ and its `plugin chain`_.

Acquisition Strategy
--------------------

The application we have in mind is a multi-dimensional continuous scan, so we
want to be able to take a number of frames with the detector driver, calculate
some statistics on them, and write them in the same dimensionality as the scan
suggests into a `NeXus`_ formatted `HDF5`_ file. The driver and each plugin in
the chain will be represented by a Block in the `hardware_layer_`, and they will
all be controlled detector Block in the `device_layer_`. This is best viewed as a
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
            detector_c [label="RunnableController"]
            DRV [label="{SimDetectorDriverPart|name: 'DRV'}"]
            POS [label="{PositionLabellerPart|name: 'POS'}"]
            STAT [label="{StatsPluginPart|name: 'STAT'}"]
            HDF [label="{HDFWriterPart|name: 'HDF'}"]
            DSET [label="{DatasetTablePart|name: 'DSET'}"]
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
`sim_detector_driver_block` and its corresponding `SimDetectorDriverPart`, and
then a `stats_plugin_block` with is corresponding `StatsPluginPart`.


The entry after this is an include. It lets us take some commonly used Blocks
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
will see out PV interface:

.. literalinclude:: ../../malcolm/modules/ADSimDetector/blocks/sim_detector_driver_block.yaml
    :language: yaml

After the parameters, defines and `StatefulController` definition, most of our
CAPart objects are instantiated in
``./malcolm/modules/ADCore/includes/adbase_parts.yaml``. Let's look at the
start of that file:

.. literalinclude:: ../../malcolm/modules/ADCore/includes/adbase_parts.yaml
    :language: yaml
    :lines: 1-34

This include structure mirrors that of the underlying templates, and allows us
to maintain a one to one mapping of YAML file to template file. If you look at
all of these CAParts you will see that they wrap up small numbers of PVs into
recognisable Attributes and Methods.

For instance:

.. literalinclude:: ../../malcolm/modules/ADCore/includes/adbase_parts.yaml
    :language: yaml
    :lines: 15-21

This corresponds to an `attribute_` that caputs to the ``NumImages`` pv with
callback when set, and uses ``NumImages_RBV`` as the current value.

Alternatively:

.. literalinclude:: ../../malcolm/modules/ADCore/includes/adbase_parts.yaml
    :language: yaml
    :lines: 22-28

This corresponds to a `method_` that caputs to the ``Acquire`` pv with callback,
and when it completes checks ``DetectorState_RBV`` to see if the detector
completed successfully or with an error.


Loading and Saving
------------------

One of the benefits of splitting the Hardware Layer from the Device Layer is
that we now get a useful interface that tells us what to load and save. We
tag all writeable CAParts as config Attributes by default, which will mean that
when we `save()` the Device Block, it will write the current value of all these
Attributes of all its child Hardware Blocks to a JSON `design_` file.

The keen eyed will notice that the top level `RunnableController` has
``config_dir`` and ``initial_design`` parameters. The first we set to
``$(yamldir)/saved_designs`` which tells us where to save and load designs from.
The second we set to ``demo_design`` which is the name design we should load at
init.

All this means that when Malcolm starts up it will apply the settings in
``./malcolm/modules/demo/saved_designs/DETECTOR/demo_design.json``. If you are
interested you can click below to expand the contents:

.. container:: toggle

    .. container:: header

        Saved Design JSON: demo_design

    .. literalinclude:: ../../malcolm/modules/demo/saved_designs/DETECTOR/demo_design.json
        :language: json

This Design will setup the plugin chain correctly for areaDetector to work the
way that Malcolm expects. In particular it makes sure that the plugins are in
the correct way that the HDF writer gets the tags it expects on each NDArray
that it receives.

.. note::

    The reason that this rewiring is done in the Design file rather than each
    plugin Part is that it allows extra plugins to be placed inline that Malcolm
    doesn't and shouldn't have to know about.


Running a Scan
--------------

First you need an areaDetector IOC. From the Diamond launcher, select
``Utilities -> GDA AreaDetector Simulation``, then click the ``Start IOC``
button.

Let's start up the example and see it in action::

    [me@mypc pymalcolm]$ ./malcolm/imalcolm.py malcolm/modules/demo/DEMO-AREADETECTOR.yaml
    Loading...
    Python 2.7.3 (default, Nov  9 2013, 21:59:00)
    Type "copyright", "credits" or "license" for more information.

    IPython 2.1.0 -- An enhanced Interactive Python.
    ?         -> Introduction and overview of IPython's features.
    %quickref -> Quick reference.
    help      -> Python's own help system.
    object?   -> Details about 'object', use 'object??' for extra details.


    Welcome to iMalcolm.

    self.mri_list:
        ['DETECTOR:DRV', 'DETECTOR:STAT', 'DETECTOR:POS', 'DETECTOR:HDF5', 'DETECTOR', 'WEB']

    Try:
    hello = self.block_view("HELLO")
    print hello.greet("me")

    or

    gui(self.block_view("COUNTER"))

    or

    self.make_proxy("localhost:8080", "HELLO")
    print self.block_view("HELLO").greet("me")


    In [1]:

Then run a scan by configuring and running with a generator. If you have
completed the `generator_tutorial` then some of the lines will be in your
`IPython`_ history and you can get them back by pressing the up arrow::

    In [1]: from scanpointgenerator import LineGenerator, CompoundGenerator

    In [2]: det = self.block_view("DETECTOR")

    In [3]: yline = LineGenerator("y", "mm", 0., 1., 6)

    In [4]: xline = LineGenerator("x", "mm", 0., 1., 5, alternate=True)

    In [5]: generator = CompoundGenerator([yline, xline], [], [], duration=0.5)

    In [6]: det.configure(generator, "/tmp", axesToMove=["x", "y"])

    In [7]: gui(det)

    In [8]: gui(self.block_view("DETECTOR:HDF5"))

We have now setup our 6x5 snake scan with 0.5 seconds per point, told Malcolm
to write the data file to the directory ``/tmp``, and that Malcolm is expected
to move the ``x`` and ``y`` axes in a continuous fashion. This means that the
detector will be configured for 30 frames that will be acquired on `run()`.

After configure, the detector will also report the datasets that it is about
to write in the ``datasets`` Attribute::

    In [9]: for col in det.datasets.value:
        print "%09s: %s" % (col, det.datasets.value[col])
       ...:
         name: ('det.data', 'det.sum', 'y.value_set', 'x.value_set')
     filename: ('det.h5', 'det.h5', 'det.h5', 'det.h5')
         type: ('primary', 'secondary', 'position_set', 'position_set')
         rank: [4 4 1 1]
         path: ('/entry/detector/detector', '/entry/sum/sum', '/entry/detector/y_set', '/entry/detector/x_set')
     uniqueid: ('/entry/NDAttributes/NDArrayUniqueId', '/entry/NDAttributes/NDArrayUniqueId', '', '')

This is saying that there is a primary dataset containing detector data in
``/entry/detector/detector`` of ``det.h5`` within the ``/tmp`` directory. It has
rank 4 (2D detector wrapped in a 2D scan), and will fill in a uniqueid dataset
``/entry/NDAttributes/NDArrayUniqueId`` each time the detector writes a new
frame. There is also a secondary (calculated) dataset called ``/entry/sum/sum``
in the same file that shares the uniqueid dataset. Finally there are a couple of
position setpoints for ``x`` and ``y`` demand values.

If you now click the Run button on the DETECTOR window you will see the scan
being performed:

.. image:: areadetector_1.png

This will write 30 frames to ``/tmp/det.h5`` (you can change the fileName within
the directory by passing it as a configure argument if you like). You can take a
look at the `HDF5`_ file to see what has been written::

    [me@mypc pymalcolm]$ module load hdf5/1-10-1
    [me@mypc pymalcolm]$ h5dump -n /tmp/det.h5
    HDF5 "/tmp/det.h5" {
    FILE_CONTENTS {
     group      /
     group      /entry
     group      /entry/NDAttributes
     dataset    /entry/NDAttributes/ColorMode
     dataset    /entry/NDAttributes/FilePluginClose
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

    [me@mypc pymalcolm]$ h5dump -d /entry/NDAttributes/NDArrayUniqueId /tmp/det.h5
    HDF5 "/tmp/det.h5" {
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
you try pausing and rewinding you will see the uniqueID number jump where you
overwrite existing frames with new frames with a greater uniqueID.

Conclusion
----------

This tutorial has given us an understanding of how `areaDetector`_ plugin
chains can be controlled in Malcolm, and how `Designs <design_>` can be loaded
and saved. In the next tutorial we will see how to create a Block in the
`scan_layer_` to co-ordinate a detector and a motor controller.







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