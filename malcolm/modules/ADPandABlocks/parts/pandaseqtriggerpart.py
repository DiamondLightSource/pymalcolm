# Treat all division as float division even in python2
from __future__ import division

from annotypes import add_call_types, Anno, TYPE_CHECKING

from malcolm.core import APartName, Block, Context, PartRegistrar
from malcolm.modules import builtin, scanning, pmac
from ..seqgenerator import SeqTriggers, DoubleBufferSeqTable

if TYPE_CHECKING:
    from typing import List, Dict

#: The SEQ.table attributes that should be present in PANDA.exports
SEQ_TABLES = ("seqTableA", "seqTableB")

with Anno("Scannable name for sequencer input"):
    APos = str

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName
AMri = builtin.parts.AMri
AInitialVisibility = builtin.parts.AInitialVisibility


def _get_blocks(context, panda_mri):
    # type: (Context, str) -> List[Block]
    """Get panda, seqA and seqB Blocks using the given context"""
    # {part_name: export_name}
    panda = context.block_view(panda_mri)
    seq_part_names = {}
    for source, export in panda.exports.value.rows():
        if export in SEQ_TABLES:
            assert source.endswith(".table"), \
                "Expected export %s to come from SEQx.table, got %s" % (
                    export, source)
            seq_part_names[source[:-len(".table")]] = export
    assert tuple(sorted(seq_part_names.values())) == SEQ_TABLES, \
        "Expected exported attributes %s, got %s" % (
            SEQ_TABLES, panda.exports.value.export)
    # {export_name: mri}
    seq_mris = {}
    for name, mri, _, _, _ in panda.layout.value.rows():
        if name in seq_part_names:
            export = seq_part_names[name]
            seq_mris[export] = mri
    assert sorted(seq_mris) == sorted(seq_part_names.values()), \
        "Couldn't find MRI for some of %s" % (seq_part_names.values(),)
    blocks = [panda]
    blocks += [context.block_view(seq_mris[x]) for x in SEQ_TABLES]
    return blocks


def doing_pcomp(row_trigger_value):
    # type: (str) -> bool
    return row_trigger_value == "Position Compare"


class PandASeqTriggerPart(builtin.parts.ChildPart):
    """Part for operating a pair of SEQ blocks in a PandA to do position
    compare at the start of each row and time based pulses within the row.
    Needs the following exports:

    - seqTableA: table Attribute of the first SEQ block
    - seqTableB: table Attribute of the second SEQ block
    - seqSetEnable: forceSet Method of an SRGATE that is used to gate both SEQs
    """

    def __init__(self, name, mri, initial_visibility=None):
        # type: (APartName, AMri, AInitialVisibility) -> None
        super(PandASeqTriggerPart, self).__init__(
            name, mri, initial_visibility=initial_visibility, stateful=False)
        # Stored generator for positions
        self.generator = None
        # The last index we have loaded
        self.loaded_up_to = 0
        # The last scan point index of the current run
        self.scan_up_to = 0
        # If we are currently loading then block loading more points
        self.loading = False
        # What is the mapping of scannable name to MotorInfo
        self.axis_mapping = {}
        # The minimum turnaround time for non-joined points
        self.min_turnaround = 0
        # The minimum time between turnaround points
        self.min_interval = 0
        # {(scannable, increasing): trigger_enum}
        self.trigger_enums = {}
        # The panda Block we will be prodding
        self.panda = None
        # The DoubleBufferSeqTable object used to load tables during a scan
        self.db_seq_table = None

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(PandASeqTriggerPart, self).setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ReportStatusHook, self.on_report_status)
        registrar.hook((scanning.hooks.ConfigureHook,
                        scanning.hooks.SeekHook,
                        scanning.hooks.PostRunArmedHook), self.on_configure)
        registrar.hook(scanning.hooks.RunHook, self.on_run)

    @add_call_types
    def on_report_status(self, context):
        # type: (scanning.hooks.AContext) -> scanning.hooks.UInfos
        child = context.block_view(self.mri)
        # Work out if we need the motor controller to send start of row triggers
        # or no triggers
        if doing_pcomp(child.rowTrigger.value):
            # Doing position compare, don't need any triggers
            trigger = scanning.infos.MotionTrigger.NONE
        else:
            # Waiting for bit at the start of each row, so need this signal
            trigger = scanning.infos.MotionTrigger.ROW_GATE
        info = scanning.infos.MotionTriggerInfo(trigger)
        return info

    def setup_pcomp_dicts(self, seqa, seqb, axis_mapping):
        """Setup the axis_mapping and trigger_enum dicts for position compare"""
        # type: (Block, Block, Dict[str, pmac.infos.MotorInfo]) -> None
        # Check that both sequencers are pointing to the same encoders
        seq_pos = {}
        for suff in "abc":
            # Something like INENC1.VAL or ZERO
            seqa_pos_inp = seqa["pos" + suff].value
            seqb_pos_inp = seqb["pos" + suff].value
            assert seqa_pos_inp == seqb_pos_inp, \
                "SeqA Pos%s = %s != SeqB Pos%s = %s" % (
                    suff, seqa_pos_inp, suff, seqb_pos_inp)
            seq_pos[seqa_pos_inp] = "POS%s" % suff.upper()

        # Fix the mres and offsets from the panda positions table
        positions_table = self.panda.positions.value
        for i, name in enumerate(positions_table.name):
            try:
                pos = seq_pos[name]
            except KeyError:
                # This is a position not connected to the seq, this is fine
                pass
            else:
                # This is a position that we can compare on, check its
                # dataset name which is the scannable name
                scannable = positions_table.datasetName[i]
                info = axis_mapping.get(scannable, None)
                if info:
                    # We are asked to scan this, so correct its resolution
                    # and store
                    info.resolution = positions_table.scale[i]
                    info.offset = positions_table.offset[i]
                    self.axis_mapping[scannable] = info
                    self.trigger_enums[(scannable, True)] = \
                        "%s>=POSITION" % pos
                    self.trigger_enums[(scannable, False)] = \
                        "%s<=POSITION" % pos
        # Check we have at least one entry
        assert self.axis_mapping, \
            "None of the seq inputs %s can be mapped to scannable names " \
            "in %s. Did you define datasetName entries for these rows in " \
            "the PandA positions table?" % (
                sorted(seq_pos), sorted(axis_mapping))

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def on_configure(self,
                     context,  # type: scanning.hooks.AContext
                     completed_steps,  # type: scanning.hooks.ACompletedSteps
                     steps_to_do,  # type: scanning.hooks.AStepsToDo
                     part_info,  # type: scanning.hooks.APartInfo
                     generator,  # type: scanning.hooks.AGenerator
                     axesToMove  # type: scanning.hooks.AAxesToMove
                     ):
        # type: (...) -> None
        self.generator = generator
        self.loaded_up_to = completed_steps
        self.scan_up_to = completed_steps + steps_to_do
        self.loading = False

        # Get the panda and the pmac we will be using
        child = context.block_view(self.mri)
        panda_mri = child.panda.value
        pmac_mri = child.pmac.value
        row_trigger = child.rowTrigger.value

        # See if there is a minimum turnaround
        infos = scanning.infos.MinTurnaroundInfo.filter_values(part_info)
        if infos:
            assert len(infos) == 1, \
                "Expected 0 or 1 MinTurnaroundInfos, got %d" % len(infos)
            self.min_turnaround = max(pmac.util.MIN_TIME, infos[0].gap)
            self.min_interval = infos[0].interval
        else:
            self.min_turnaround = pmac.util.MIN_TIME
            self.min_interval = pmac.util.MIN_INTERVAL

        # Get panda Block, and the sequencer Blocks so we can do some checking
        self.panda, seqa, seqb = _get_blocks(context, panda_mri)

        # Fill in motor infos and trigger lookups
        motion_axes = pmac.util.get_motion_axes(generator, axesToMove)
        self.axis_mapping = {}
        self.trigger_enums = {}

        if motion_axes:
            # Need to fill in the axis mapping
            axis_mapping = pmac.util.cs_axis_mapping(
                context, context.block_view(pmac_mri).layout.value, motion_axes)
            if doing_pcomp(row_trigger):
                # We need to do position compare, so only place the infos into
                # axis_mapping that our sequencer can see
                self.setup_pcomp_dicts(seqa, seqb, axis_mapping)
            else:
                # We rely on the inputs coming into SEQ bitA
                assert seqa["bita"].value == seqb["bita"].value != "ZERO", \
                    "SEQ.bita inputs need to point to the same non-zero input"
                self.axis_mapping = axis_mapping

        # TODO:
        # Check that the sequencer blocks have the correct wiring, delays, and
        # setup monitors on the active field
        assert seqa
        assert seqb

        # load up the first SEQ
        seq_triggers = SeqTriggers(self.generator, self.axis_mapping,
                                   self.trigger_enums, self.min_turnaround,
                                   self.min_interval)

        rows_gen = seq_triggers.get_rows(self.loaded_up_to, self.scan_up_to)

        self.db_seq_table = DoubleBufferSeqTable(self.panda[SEQ_TABLES[0]],
                                                 self.panda[SEQ_TABLES[1]])

        self.db_seq_table.configure(rows_gen)

    @add_call_types
    def on_run(self, context):
        # type: (scanning.hooks.AContext) -> None
        # self.double_buf_seq.run()
        # Call sequence table enable
        self.panda.seqSetEnable()
        self.db_seq_table.run()

    # @add_call_types
    # def on_reset(self, context):
    #     # type: (builtin.hooks.AContext) -> None
    #     super(PandASeqTriggerPart, self).on_reset(context)
    #     self.on_abort(context)

    # @add_call_types
    # def on_abort(self, context):
    #     # type: (builtin.hooks.AContext) -> None
    #     self.double_buf_seq.abort()
