.. _panda_tutorial:

PandA Tutorial
==============

You should already know how to create a `block_` in the `scan_layer_` that
can control a Delta Tau PMAC, sending triggers to a PandABox_ and capturing
encoder positions. We now move onto using the PandA in a more intelligent way,
listening to the encoder positions, and generating the trigger stream itself.

Strategy
--------

Imagine a 2D Grid scan. The strategy for this trigger scheme is that at the
start of each row, PandA should do a position compare on the axis that moves
most, then generate a series of time based triggers during the row. During the
turnaround it should then wait until the motor has cleared the start of the
next row before doing a position compare on that value.

This strategy can be extended to any sort of scan trajectory. It is implemented
by Malcolm generating a table of sequencer rows, with 3 sequencer rows per scan
section without gaps:

1. Compare on the lower bound of the motor that moves by the biggest number of
   counts during the first point of the row, producing one live trigger pulse
2. Produce the rest of the live triggers for the row
3. Produce a dead trigger for the start of the turnaround, waiting for the
   amount of time that the motor is going in the wrong direction during the
   turnaround

Adding to the a scan Block
--------------------------

In the `pmac_tutorial` you should have created a ``scan_block.yaml`` in the
``etc/malcolm/blocks`` subdirectory. We will now add a new `panda_pcomp_block`
and its corresponding `PandAPcompPart` to it. It will hold the `mri_` of the
PandA and Brick that are performing the scan, and will set the PandA sequencer
tables to the correct values::

    ...

    - scanning.parts.DetectorChildPart:
        name: PANDA-01
        mri: BLxxI-ML-PANDA-01
        initial_visibility: True

    - ADPandABlocks.blocks.panda_pcomp_block:
        mri: $(mri_prefix):PCOMP
        panda: BLxxI-ML-PANDA-01
        pmac: BLxxI-ML-BRICK-01

    # Make this initially invisible so it doesn't disturb existing scans
    - ADPandABlocks.parts.PandAPcompPart:
        name: PCOMP
        mri: $(mri_prefix):PCOMP
        initial_visibility: False

The `DetectorChildPart` definition for the PandA is unchanged, the PCOMP Block
purely holds the data of which panda and which pmac to use, so all of the logic
is contained in the PCOMP Part.

.. note::

    The PandAPcompPart has initial_visibility set to False. This is because we
    are adding this Part to an existing scan Block definition, which already has
    instances and possibly saved configs. Loading a saved config will only
    affect Parts and Blocks contained within it, so any existing saved config
    will not touch this new PCOMP Part. If it was visible, it would contribute
    to the existing scans too, which would make them error as the PandA wouldn't
    have been setup for it.

Setup the Devices
-----------------

We can now run up imalcolm by executing ``etc/malcolm/BLxxI-ML-MALC-01.yaml``,
and open http://localhost:8008/gui/BLxxI-ML-SCAN-01 to see our scan Block.
First, just check that the config we saved in the previous tutorial still works.
It should run with no modifications. If this is all fine, we can move onto
setting up the motion controller. We can start from our previous co-ordinate
system design, then just uncheck the ``Output Triggers`` Attribute:

.. image:: panda_0.png

We can then navigate back up and to the PandA, and load the `template_design_`
``template_double_seq_pcomp``:

.. image:: panda_1.png



This design assumes you have the live and dead frame signals from the PMAC
connected to TTLIN1 and TTLIN2. If this is not the case, you can connect them
to the correct inputs, like the FMC_24V_IN signals for example.

Each rising edge of a live frame generates a short trigger pulse, which is sent
to a detector on TTLOUT2. Again, you can connect detectors on different outputs
to this signal. The reason we don't connect it directly to the live frame signal
is because when you interrupt the PMAC it doesn't reset the GPIOs, and the arm
of the detector may come before these signals are reset, creating one false
trigger.

Next we come to the Frame Gate. This is set high by a live frame pulse, and
set low by a dead frame. It will be high for an entire series of joined frames,
and low during the turnarounds. We use this to gate the PCAP averaging of
positions so they are not averaged during the turnarounds.

Fed from this is the End of Frame signal. This fires whenever we get a live or
dead frame signal, but not while the Frame Gate is active. This effectively
means we will get a short pulse at the end of each frame, which we use to
trigger PCAP to output the current capture values, and advance to the next
frame.

Now we have changed the inputs and outputs to this chain of Blocks, we can
save the design with a new name.

Setup the Scan
--------------

Now we have setup each Block in the `device_layer_`, it is time to setup the
Scan Block. We do this by:

- Setting the scan ``Label`` to a suitable short phrase that can be placed on
  a GDA GUI. E.g. "Small stage tomography", or "Fine stage XRF + Imaging"
- Setting ``Simultaneous Axes`` to the scannable names of all of the motors
  in the CS with fastest moving motor first, like
  ``["stagex", "stagey", "stagez"]``
- Saving the design with a name that is similar to the label. E.g. "t1_tomo" or
  "t2_xspress3_excalibur"

This will make a saved config that captures the device design names::

    {
      "attributes": {
        "layout": {
          "BRICK-01": {
            "x": 0.0,
            "y": 139.60000610351562,
            "visible": true
          },
          "PANDA-01": {
            "x": 0.0,
            "y": 0.0,
            "visible": true
          }
        },
        "exports": {},
        "simultaneousAxes": [
           "stagea",
           "stagex"
        ],
        "label": "PMAC Master Tomography"
      },
      "children": {
        "BRICK-01": {
          "design": "a_z_in_cs1"
        },
        "PANDA-01": {
          "design": "pmac_master",
          "attributesToCapture": {
            "typeid": "malcolm:core/Table:1.0",
            "name": [],
            "sourceId": [],
            "description": [],
            "sourceType": [],
            "dataType": [],
            "datasetType": []
          }
        }
      }
    }

We can now run a test scan to make sure the correct data is produced, either
with a generator on the commandline, or with the Web GUI, as in previous
tutorials. If it all works as expected, we can set the ``initial_design`` for
this scan instance in ``etc/malcolm/BLxxI-ML-MALC-01.yaml``::

    ...

    # Define the Scans
    - BLxxI.blocks.scan_block:
        mri_prefix: BLxxI-ML-SCAN-01
        config_dir: $(config_dir)
        initial_design: pmac_master_tomo

    # More scans here...

    ...

If we need a similar scan with a different set of detectors active, we can
just make a new instance of the same scan block, repeat the setup scan steps
with a new label and design name, and save this design in a similar way.

Conclusion
----------
This tutorial has given us an understanding of how to perform a scan with the
PMAC acting as master, sending trigger pulses to a PandA. We are limited to
about 300Hz as we have to send all the points down to the PMAC via the
trajectory scan. In the next tutorial we will see how the PandA can act as
master, using the positions from the encoders to generate pulses, allowing
kHz rates of scanning.

.. _GeoBrick LV IMS-II:
    http://faradaymotioncontrols.co.uk/geo-brick-lv/

.. _PandABox:
    https://www.ohwr.org/project/pandabox/wikis/home

.. _PEP 20:
    https://www.python.org/dev/peps/pep-0020/

.. _EPICS pmac:
    https://github.com/dls-controls/pmac

.. _ADPandaBlocks:
    https://github.com/PandABlocks/ADPandABlocks