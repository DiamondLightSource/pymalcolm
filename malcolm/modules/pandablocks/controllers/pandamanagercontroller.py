import time

from annotypes import Anno, TYPE_CHECKING
from cothread.cosocket import socket

from malcolm.core import Queue, TimeoutError, TimeStamp, NumberMeta, Widget, \
    Display
from malcolm.modules import builtin
from .pandablockcontroller import PandABlockController
from ..parts.pandaactionpart import PandAActionPart
from ..parts.pandabussespart import PandABussesPart
from ..pandablocksclient import PandABlocksClient
from ..util import DOC_URL_BASE, ADocUrlBase

if TYPE_CHECKING:
    from typing import Sequence, Tuple, Dict, Set

with Anno("Hostname of the box"):
    AHostname = str
with Anno("Port number of the TCP server control port"):
    APort = int
with Anno("Time between polls of PandA current value changes"):
    APollPeriod = float


AMri = builtin.controllers.AMri
AConfigDir = builtin.controllers.AConfigDir
ATemplateDesigns = builtin.controllers.ATemplateDesigns
AInitialDesign = builtin.controllers.AInitialDesign
AUseGit = builtin.controllers.AUseGit
ADescription = builtin.controllers.ADescription


# Minimum period in seconds between updates of the last poll period attribute
POLL_PERIOD_REPORT = 1


class PandAManagerController(builtin.controllers.ManagerController):
    def __init__(self,
                 mri,  # type: AMri
                 config_dir,  # type: AConfigDir
                 hostname="localhost",  # type: AHostname
                 port=8888,  # type: APort
                 doc_url_base=DOC_URL_BASE,  # type: ADocUrlBase
                 poll_period=0.1,  # type: APollPeriod
                 template_designs="",  # type: ATemplateDesigns
                 initial_design="",  # type: AInitialDesign
                 use_git=True,  # type: AUseGit
                 description="",  # type: ADescription
                 ):
        # type: (...) -> None
        super(PandAManagerController, self).__init__(
            mri=mri,
            config_dir=config_dir,
            template_designs=template_designs,
            initial_design=initial_design,
            use_git=use_git,
            description=description,
        )
        self._poll_period = poll_period
        self._doc_url_base = doc_url_base
        # All the bit_out fields and their values
        # {block_name.field_name: value}
        self._bit_outs = {}  # type: Dict[str, bool]
        # The bit_out field values that need toggling since the last handle
        # {block_name.field_name: value}
        self._bit_out_changes = {}  # type: Dict[str, bool]
        # The fields that busses needs to know about
        # {block_name.field_name[.subfield_name]}
        self._bus_fields = set()  # type: Set[str]
        # The child controllers we have created
        self._child_controllers = {}  # type: Dict[str, PandABlockController]
        # The PandABlock client that does the comms
        self._client = PandABlocksClient(hostname, port, Queue)
        # Filled in on reset
        self._stop_queue = None
        self._poll_spawned = None
        # Poll period reporting
        self.last_poll_period = NumberMeta(
            "float64", "The time between the last 2 polls of the hardware",
            tags=[Widget.TEXTUPDATE.tag()],
            display=Display(units="s", precision=3)
        ).create_attribute_model(poll_period)
        self.field_registry.add_attribute_model(
            "lastPollPeriod", self.last_poll_period)
        # Bus tables
        self.busses = self._make_busses()  # type: PandABussesPart
        self.add_part(self.busses)

    def do_init(self):
        # start the poll loop and make block parts first to fill in our parts
        # before calling _set_block_children()
        self.start_poll_loop()
        super(PandAManagerController, self).do_init()

    def start_poll_loop(self):
        # queue to listen for stop events
        if not self._client.started:
            self._stop_queue = Queue()
            if self._client.started:
                self._client.stop()
            self._client.start(self.process.spawn, socket)
        if not self._child_controllers:
            self._make_child_controllers()
        if self._poll_spawned is None:
            self._poll_spawned = self.process.spawn(self._poll_loop)

    def do_disable(self):
        super(PandAManagerController, self).do_disable()
        self.stop_poll_loop()

    def do_reset(self):
        self.start_poll_loop()
        super(PandAManagerController, self).do_reset()

    def _poll_loop(self):
        """At self.poll_period poll for changes"""
        last_poll_update = time.time()
        next_poll = time.time() + self._poll_period
        try:
            while True:
                # Need to make sure we don't consume all the CPU, allow us to be
                # active for 50% of the poll period, so we must sleep at least
                # 50% of the poll period
                min_sleep = self._poll_period * 0.5
                sleep_for = next_poll - time.time()
                if sleep_for < min_sleep:
                    # Going too fast, slow down a bit
                    last_poll_period = self._poll_period + min_sleep - sleep_for
                    sleep_for = min_sleep
                else:
                    last_poll_period = self._poll_period
                try:
                    # If told to stop, we will get something here and return
                    return self._stop_queue.get(timeout=sleep_for)
                except TimeoutError:
                    # No stop, no problem
                    pass
                # Poll for changes
                self.handle_changes(self._client.get_changes())
                if last_poll_period != self.last_poll_period.value and \
                        next_poll - last_poll_update > POLL_PERIOD_REPORT:
                    self.last_poll_period.set_value(last_poll_period)
                    last_poll_update = next_poll
                next_poll += last_poll_period
        except Exception as e:
            self.go_to_error_state(e)
            raise

    def stop_poll_loop(self):
        if self._poll_spawned:
            self._stop_queue.put(None)
            self._poll_spawned.wait()
            self._poll_spawned = None
        if self._client.started:
            self._client.stop()

    def _make_child_controllers(self):
        self._child_controllers = {}
        pos_names = []
        blocks_data = self._client.get_blocks_data()
        for block_rootname, block_data in blocks_data.items():
            block_names = []
            if block_data.number == 1:
                block_names.append(block_rootname)
            else:
                for i in range(block_data.number):
                    block_names.append("%s%d" % (block_rootname, i + 1))
            for block_name in block_names:
                # Look through the BlockData for things we are interested in
                for field_name, field_data in block_data.fields.items():
                    if field_data.field_type == "pos_out":
                        pos_names.append("%s.%s" % (block_name, field_name))

                # Make the child controller and add it to the process
                controller, child_part = self._make_child_block(
                    block_name, block_data)
                self.process.add_controller(controller, timeout=5)
                self._child_controllers[block_name] = controller
                # If there is only one, make an alias with "1" appended for
                # *METADATA.LABEL lookup
                if block_data.number == 1:
                    self._child_controllers[block_name + "1"] = controller
                self.add_part(child_part)

        # Create the busses from their initial sets of values
        pcap_bit_fields = self._client.get_pcap_bits_fields()
        self.busses.create_busses(pcap_bit_fields, pos_names)
        # Handle the pos_names that busses needs
        self._bus_fields = set(pos_names)
        for pos_name in pos_names:
            for suffix in ("CAPTURE", "UNITS", "SCALE", "OFFSET"):
                self._bus_fields.add("%s.%s" % (pos_name, suffix))
        # Handle the bit_outs, keeping a list for toggling and adding them
        # to the set of things that the busses need
        self._bit_outs = {k: 0 for k in self.busses.bits.value.name}
        self._bit_out_changes = {}
        self._bus_fields |= set(self._bit_outs)
        for capture_field in pcap_bit_fields:
            self._bus_fields.add(capture_field)
        # Handle the initial set of changes to get an initial value
        self.handle_changes(self._client.get_changes())
        # Then once more to let bit_outs toggle back
        self.handle_changes(())
        assert not self._bit_out_changes, \
            "There are still bit_out changes %s" % self._bit_out_changes

    def _make_busses(self):
        # type: () -> PandABussesPart
        return PandABussesPart("busses", self._client)

    def _make_child_block(self, block_name, block_data):
        controller = PandABlockController(
            self._client, self.mri, block_name, block_data, self._doc_url_base)
        if block_name == "PCAP":
            controller.add_part(PandAActionPart(
                self._client, "*PCAP", "ARM", "Arm position capture", []))
            controller.add_part(PandAActionPart(
                self._client, "*PCAP", "DISARM", "Disarm position capture", []))
        child_part = builtin.parts.ChildPart(
            name=block_name, mri=controller.mri, stateful=False)
        return controller, child_part

    def _handle_change(self, k, v, bus_changes, block_changes, bit_out_changes):
        # Handle bit changes
        try:
            current_v = self._bit_outs[k]
        except KeyError:
            # Not a bit
            pass
        else:
            # Convert to a boolean
            v = bool(int(v))
            try:
                changed_to = bit_out_changes[k]
            except KeyError:
                # We didn't already make a change
                if v == current_v:
                    # Value is the same, store the negation, and set it
                    # back next time
                    self._bit_out_changes[k] = v
                    v = not v
            else:
                # Already made a change, defer this value til next time
                # if it is different
                if changed_to != v:
                    self._bit_out_changes[k] = v
                return
            self._bit_outs[k] = v

        # Notify the bus tables if they need to know
        if k in self._bus_fields:
            bus_changes[k] = v

        # Add to the relevant Block changes dict
        block_name, field_name = k.split(".", 1)
        if block_name == "*METADATA":
            if field_name.startswith("LABEL_"):
                field_name, block_name = field_name.split("_", 1)
            else:
                # Don't support any non-label metadata fields at the moment
                return
        block_changes.setdefault(block_name, {})[field_name] = v

    def handle_changes(self, changes):
        # type: (Sequence[Tuple[str, str]]) -> None
        ts = TimeStamp()
        # {block_name: {field_name: field_value}}
        block_changes = {}
        # {full_field: field_value}
        bus_changes = {}

        # Process bit outs that need changing
        bit_out_changes = self._bit_out_changes
        self._bit_out_changes = {}
        for k, v in bit_out_changes.items():
            self._bit_outs[k] = v
            bus_changes[k] = v
            block_name, field_name = k.split(".")
            block_changes.setdefault(block_name, {})[field_name] = v

        # Work out which change is needed for which block
        for k, v in changes:
            self._handle_change(
                k, v, bus_changes, block_changes, bit_out_changes)

        # Notify the Blocks that they need to handle these changes
        if bus_changes:
            self.busses.handle_changes(bus_changes, ts)
        for block_name, changes in block_changes.items():
            self._child_controllers[block_name].handle_changes(changes, ts)
