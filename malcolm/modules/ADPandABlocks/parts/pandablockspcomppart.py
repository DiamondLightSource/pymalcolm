from annotypes import add_call_types

from malcolm.core import APartName
from malcolm.modules import builtin, scanning

#: The SEQ.table attributes that should be present in PANDA.exports
SEQ_TABLES = ("seqTableA", "seqTableB")


class PandABlocksPcompPart(builtin.parts.ChildPart):
    """Part for controlling a `stats_plugin_block` in a Device"""

    def __init__(self, name, mri):
        # type: (APartName, builtin.parts.AMri) -> None
        super(PandABlocksPcompPart, self).__init__(name, mri)
        # Stored generator for positions
        self.generator = None
        # The last index we have loaded
        self.loaded_up_to = 0
        # The last scan point index of the current run
        self.scan_up_to = 0
        # If we are currently loading then block loading more points
        self.loading = False
        # The mri of the panda we should be prodding
        self.panda_mri = None
        # The mris of the sequencers we will be using
        self.seqa_mri = None
        self.seqb_mri = None
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
        # TODO: check for motor info and store
        assert part_info
        # TODO: store here?
        assert axesToMove
        # Our PandA might not be wired up yet, so this is as far as
        # we can get
        self.panda_mri = context.block_view(self.mri).panda.value

    def _get_seq_mris(self, context):
        # {part_name: export_name}
        panda = context.block_view(self.panda_mri)
        seq_part_names = {}
        for source, export in panda.exports.value.rows():
            if export in SEQ_TABLES:
                assert source.endswith(".table"), \
                    "Expected export %s to come from SEQx.table, got %s" %(
                        export, source)
                seq_part_names[source[:-len(".table")]] = export
        assert sorted(seq_part_names.values()) == SEQ_TABLES, \
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
        return seq_mris

    @add_call_types
    def post_configure(self, context):
        # type: (scanning.hooks.AContext) -> None
        seq_mris = self._get_seq_mris(context)
        self.seqa_mri = seq_mris[SEQ_TABLES[0]]
        self.seqb_mri = seq_mris[SEQ_TABLES[1]]
        # load up the first SEQ
        self._fill_sequencer()

    @add_call_types
    def run(self, context):
        # type: (scanning.hooks.AContext) -> None
        panda = context.block_view(self.panda_mri)

