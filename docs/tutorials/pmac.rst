.. _pmac_tutorial:

PMAC Tutorial
=============

You should already know how to create a `block_` in the `scan_layer_` that
can control multiple Detectors, and control a dummy motor controller. Let's
look at how we can control a real motor controller (a Delta Tau Turbo PMAC
based system like the `GeoBrick LV IMS-II`_) and capture encoder positions with
a PandABox_.


Make a Malcolm directory for a beamline
---------------------------------------

The first thing we need is a directory for our beamline specific Blocks and
`process_definition_` to live in. At DLS we will typically make a directory
``etc/malcolm`` in the ``BL`` IOC directory for this purpose, but it could be
anywhere. We will refer to this directory as ``etc/malcolm`` for the rest of
the tutorial. We will also create an ``etc/malcolm/blocks`` subdirectory for
any beamline specific Blocks we create.


Define the Process Definition
-----------------------------

.. highlight:: yaml

Let's make a Process Definition in ``etc/malcolm/BLxxI-ML-MALC-01.yaml``::

    #!/dls_sw/prod/common/python/RHEL7-x86_64/pymalcolm/4-0/malcolm/imalcolm.py

    # Define the directory that this YAML file lives in as a Malcolm module
    # so we can use Blocks defined there as BLxxI.blocks.yyy
    - builtin.defines.module_path:
        name: BLxxI
        path: $(yamldir)

    # This is where all the saved and loaded designs will live
    - builtin.defines.string:
        name: config_dir
        value: /dls_sw/ixx/epics/malcolm

    # Define the motion controllers
    - BLxxI.blocks.brick01_block:
        mri_prefix: BLxxI-ML-BRICK-01
        pv_prefix: BLxxI-MO-BRICK-01
        config_dir: $(config_dir)

    # More motion controllers here...

    # Define the Detectors
    - ADPandABlocks.blocks.pandablocks_runnable_block:
        mri_prefix: BLxxI-ML-PANDA-01
        pv_prefix: BLxxI-MO-PANDA-01
        hostname: blxxi-mo-panda-01
        config_dir: $(config_dir)

    # More non-panda detectors here...

    # Define the Scans
    - BLxxI.blocks.pmac_master_scan_block:
        mri_prefix: BLxxI-ML-SCAN-01
        config_dir: $(config_dir)
        initial_design:

    # More scans here...

    # Define the ServerComms
    - web.blocks.web_server_block:
        mri: $(yamlname):WEB

    - pva.blocks.pva_server_block:
        mri: $(yamlname):PVA

The first thing to note is the ``#!`` line at the top of the file. This means
that we can make the YAML file executable, and when it is executed
``imalcolm.py`` will be run with the path of the YAML file passed as an
argument. The full path to ``imalcolm.py`` allows us to pin to a particular
version of Malcolm.

After this, we've defined a ``BLxxI`` module, and created two beamline specific
Blocks from it (``brick01_block`` and ``pmac_master_scan_block``), and then
created three Blocks from definitions already in Malcolm (
``pandablocks_runnable_block``, ``web_server_block``, ``pva_server_block``).
Let's look at how those beamline specific Blocks are defined.


Define a PMAC Block
-------------------

In the ``etc/malcolm/blocks`` subdirectory we will make ``brick01_block.yaml``::

    - builtin.parameters.string:
        name: mri_prefix
        description: MRI for created block

    - builtin.parameters.string:
        name: pv_prefix
        description: PV prefix that was used to construct the pmac controller

    - builtin.parameters.string:
        name: config_dir
        description: Where to store saved configs

    - builtin.controllers.ManagerController:
        mri: $(mri_prefix)
        config_dir: $(config_dir)

    # Label so that we can tell at a glance what this PMAC controls at runtime
    - builtin.parts.LabelPart:
        value: Brick with X and Y Sample stage motors

    # Raw motor Blocks and their corresponding Parts
    - pmac.includes.rawmotor_collection:
        mri: BLxxI-ML-STAGE-01:X
        prefix: BLxxI-MO-STAGE-01:X
        scannable: stagex

    - pmac.includes.rawmotor_collection:
        mri: BLxxI-ML-STAGE-01:Y
        prefix: BLxxI-MO-STAGE-01:Y
        scannable: stagey

    # Co-ordinate system Block and its corresponding Part
    - pmac.includes.cs_collection:
        mri_prefix: $(mri_prefix)
        pv_prefix: $(pv_prefix)
        cs: 1

    # Trajectory scan and status Blocks and their corresponding Parts
    - pmac.includes.trajectory_collection:
        mri_prefix: $(mri_prefix)
        pv_prefix: $(pv_prefix)


Here we are constructing a Block specific to ``BLxxI-MO-BRICK-01``. We still
pass in ``mri_prefix`` and ``pv_prefix`` because it makes it easier to see
from the top level what is creating what.

We then create a `ManagerController`, with a number of child Blocks and Parts
(produced by ``includes``) that represent raw motors, co-ordinate systems,
the trajectory scan and PMAC status EPICS templates.


Define a scan Block
-------------------

In the ``etc/malcolm/blocks`` subdirectory we will also make
``pmac_master_scan_block.yaml``::

    - builtin.parameters.string:
        name: mri_prefix
        description: MRI for created block

    - builtin.parameters.string:
        name: config_dir
        description: Where to store saved configs

    - builtin.parameters.string:
        name: initial_design
        description: Initial design to load for the scan

    - scanning.controllers.RunnableController:
        mri: $(mri_prefix)
        config_dir: $(config_dir)
        description: |
          Hardware triggered scan, with PMAC providing trigger signals at
          up to 300Hz

    - builtin.parts.LabelPart:

    - scanning.parts.SimultaneousAxesPart:

    - scanning.parts.DatasetTablePart:
        name: DSET

    - pmac.parts.PmacChildPart:
        name: BRICK-01
        mri: BLxxI-ML-BRICK-01
        initial_visibility: True

    - scanning.parts.DetectorChildPart:
        name: PANDA-01
        mri: BLxxI-ML-PANDA-01
        initial_visibility: True


Again we take the ``mri_prefix`` and ``config_dir`` needed to create the Block,
but this time we also take an ``initial_design``. This will allow us to create
multiple instances of this scan Block with different configurations, and load
the correct configuration for each Block.




Expose Blocks in a module
-------------------------

We've made two YAML files


Setup PandA
-----------


Conclusion
----------



.. _GeoBrick LV IMS-II:
    http://faradaymotioncontrols.co.uk/geo-brick-lv/

.. _PandABox:
    https://www.ohwr.org/project/pandabox/wikis/home