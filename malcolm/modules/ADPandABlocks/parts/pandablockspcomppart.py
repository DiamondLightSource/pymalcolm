# Treat all division as float division even in python2
from __future__ import division

from annotypes import add_call_types, Anno, TYPE_CHECKING
from scanpointgenerator import Point

from malcolm.core import APartName, Block
from malcolm.modules import builtin, scanning, pmac

from ..util import SequencerTable, Trigger

if TYPE_CHECKING:
    from typing import List, Tuple

#: The SEQ.table attributes that should be present in PANDA.exports
SEQ_TABLES = ("seqTableA", "seqTableB")

#: The number of sequencer table rows
SEQ_TABLE_ROWS = 1024

with Anno("Scannable name for sequencer input"):
    APos = str


# The triggers if pos >= position
POS_GT = [Trigger.POSA_GT, Trigger.POSB_GT, Trigger.POSC_GT]
POS_LT = [Trigger.POSA_LT, Trigger.POSB_LT, Trigger.POSC_LT]

# How long is a single tick if prescaler is 0
TICK = 8e-9

# Minimum number of ticks for a phase
MIN_PHASE = 1

# Maximum repeats
MAX_REPEATS = 4096

# Minimum gap between rows in seconds
MIN_GAP = 0.1


def gap_row(duration=MIN_PHASE * 2):
    # type: (int) -> List
    # Reset PCAP triggers, then wait for a bit before advancing
    phase2 = duration - MIN_PHASE
    row = [1, Trigger.IMMEDIATE, 0,
           # Phase1: Live=0, Gate=0, PCAP_Trig=1
           # This triggers PCAP for the last point, resetting detector and
           # gate signals
           MIN_PHASE, 0, 0, 1, 0, 0, 0,
           # Phase2: Live=0, Gate=1, PCAP_Trig=0
           # This resets PCAP trigger
           phase2, 0, 0, 0, 0, 0, 0]
    return row


def compare_row(half_frame, position, trigger_enum):
    # type: (int, int, Trigger) -> List
    # Put in a compare point for the lower bound
    row = [1, trigger_enum, position,
           # Phase1: Live=1, Gate=1, PCAP_Trig=0
           # This triggers detector and starts gate for row
           half_frame, 1, 1, 0, 0, 0, 0,
           # Phase2: Live=0, Gate=1, PCAP_Trig=0
           # This resets the detector trigger and keeps gate high
           half_frame, 0, 1, 0, 0, 0, 0]
    return row


def time_row(half_frame):
    # type: (int) -> List
    # Put in a compare point for the lower bound
    row = [1, Trigger.IMMEDIATE, 0,
           # Phase1: Live=1, Gate=1, PCAP_Trig=1
           # This triggers PCAP for the last point and the detector for this
           # point while keeping gate high
           half_frame, 1, 1, 1, 0, 0, 0,
           # Phase2: Live=0, Gate=1, PCAP_Trig=0
           # This resets PCAP and detector signal while keeping gate high
           half_frame, 0, 1, 0, 0, 0, 0]
    return row


class PandABlocksPcompPart(builtin.parts.ChildPart):
    """Part for operating a pair of SEQ blocks in a PandA to do position
    compare"""

    def __init__(self, name, mri, posa, posb="", posc=""):
        # type: (APartName, builtin.parts.AMri, APos, APos, APos) -> None
        super(PandABlocksPcompPart, self).__init__(name, mri, stateful=False)
        # Store scannable names
        self.scannables = (posa, posb, posc)
        self.trigger_enums = {
            (posa, True): Trigger.POSA_GT,
            (posa, False): Trigger.POSA_LT,
            (posb, True): Trigger.POSB_GT,
            (posb, False): Trigger.POSB_LT,
            (posc, True): Trigger.POSC_GT,
            (posc, False): Trigger.POSC_LT,
        }
        # Stored generator for positions
        self.generator = None
        # The last index we have loaded
        self.loaded_up_to = 0
        # The last scan point index of the current run
        self.scan_up_to = 0
        # If we are currently loading then block loading more points
        self.loading = False
        # The last point we loaded
        self.last_point = None
        # What is the mapping of scannable name to MotorInfo
        self.axis_mapping = None
        # The mri of the panda we should be prodding
        self.panda_mri = None
        # The sequencer tables
        self.seq_tables = []
        # Hooks
        self.register_hooked(scanning.hooks.ConfigureHook,
                             self.configure)
        self.register_hooked(scanning.hooks.PostConfigureHook,
                             self.post_configure)
        self.register_hooked(scanning.hooks.RunHook,
                             self.run)

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def configure(self,
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
        self.last_point = None
        _, self.axis_mapping = pmac.util.cs_axis_mapping(part_info, axesToMove)
        # Our PandA might not be wired up yet, so this is as far as
        # we can get
        self.panda_mri = context.block_view(self.mri).panda.value

    def _get_blocks(self, context):
        # {part_name: export_name}
        panda = context.block_view(self.panda_mri)
        seq_part_names = {}
        for source, export in panda.exports.value.rows():
            if export in SEQ_TABLES:
                assert source.endswith(".table"), \
                    "Expected export %s to come from SEQx.table, got %s" %(
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
        # TODO: check wiring delays, prescalers
        return blocks

    @add_call_types
    def post_configure(self, context):
        # type: (scanning.hooks.AContext) -> None
        panda, seqa, seqb = self._get_blocks(context)
        self.seq_tables = [panda[attr] for attr in SEQ_TABLES]
        # load up the first SEQ
        self._fill_sequencer(self.seq_tables[0])

    def _what_moves_most(self, point):
        # type: (Point) -> Tuple[int, Trigger, int]
        # {axis_name: abs(diff_cts)}
        diffs = {}
        # {axis_name: compare_cts}
        positions = {}
        # {axis_name: dir}
        increasings = {}
        for i, s in enumerate(self.scannables):
            # For each position our sequencers are connected to
            try:
                info = self.axis_mapping[s]
            except KeyError:
                # This axis isn't moving in this scan, ignore it
                pass
            else:
                compare_cts = round(point.lower[s] / info.resolution)
                centre_cts = round(point.positions[s] / info.resolution)
                diff_cts = centre_cts - compare_cts
                diffs[s] = abs(diff_cts)
                positions[s] = compare_cts
                increasings[s] = diff_cts > 0
        assert diffs, \
            "Can't work out a compare point for %s" % point.positions
        # Sort on abs(diff), take the biggest
        axis_name = sorted(diffs, key=diffs.get)[-1]
        increasing = increasings[axis_name]
        trigger_enum = self.trigger_enums[(axis_name, increasing)]
        if self.last_point:
            # TODO: what about pmactrajectorypart min_turnaround?
            time_arrays, velocity_arrays = pmac.util.profile_between_points(
                self.axis_mapping, self.last_point, point)
            time_array = time_arrays[axis_name]
            velocity_array = velocity_arrays[axis_name]
            # Work backwards through the velocity array until we are going the
            # opposite way
            i = 0
            for i, v in reversed(list(enumerate(velocity_array))):
                if (increasing and v <= 0) or (not increasing and v >= 0):
                    # The axis is stationary or going the wrong way at this
                    # point, so we should be blind before then
                    assert i < len(velocity_array) - 1, \
                        "Last point of %s is wrong direction" % velocity_array
                    break
            blind = round(time_array[i] / TICK)
        else:
            blind = 0
        return blind, trigger_enum, positions[axis_name]

    def _fill_sequencer(self, seq_table):
        # type: (Block) -> None
        rows = []
        for i in range(self.loaded_up_to, self.scan_up_to):
            point = self.generator.get_point(i)
            half_frame = round(point.duration / TICK / 2)
            if self.last_point is None or not pmac.util.points_joined(
                    self.axis_mapping, self.last_point, point):
                # First row, or rows not joined
                # Work out which axis moves most, returning how long to be blind
                # for in the turnaround, the trigger enum and compare point
                blind, trigger_enum, position = self._what_moves_most(point)
                if self.last_point is not None:
                    # Be blind for most of the turnaround
                    rows.append(gap_row(blind))
                # Create a compare point for the next row
                rows.append(compare_row(half_frame, position, trigger_enum))
            elif rows and rows[-1][1] == Trigger.IMMEDIATE and \
                    rows[-1][3] == half_frame and rows[-1][0] < MAX_REPEATS:
                # Repeated frame, just increment the last row repeats
                rows[-1][0] += 1
            else:
                # New time section
                rows.append(time_row(half_frame))
            if i == self.scan_up_to - 1:
                # Last row, reset the PCAP triggers
                rows.append(gap_row())
            self.last_point = point
            if len(rows) > SEQ_TABLE_ROWS - 3:
                # If we don't have enough space for more rows, stop here
                break

        table = SequencerTable.from_rows(rows)
        seq_table.put_value(table)

    @add_call_types
    def run(self, context):
        # type: (scanning.hooks.AContext) -> None
        panda = context.block_view(self.panda_mri)


