import time

from malcolm.compat import OrderedDict
from malcolm.controllers.builtin import StatefulController, BaseController, \
    ManagerController
from malcolm.core import method_also_takes, Queue, TimeoutError, \
    call_with_params
from malcolm.parts.pandablocks.pandablocksmaker import PandABlocksMaker
from malcolm.vmetas.builtin import BooleanMeta, TableMeta, StringMeta, \
    NumberMeta
from .pandablocksclient import PandABlocksClient


@method_also_takes(
    "hostname", StringMeta("Hostname of the box"), "localhost",
    "port", NumberMeta("uint32", "Port number of the server client"), 8888,
    "areaDetectorPrefix",
        StringMeta("Prefix for areaDetector records, if using EPICS"), ""
)
class PandABlocksController(ManagerController):
    def __init__(self, process, parts, params):
        super(PandABlocksController, self).__init__(process, parts, params)
        # {block_name: BlockData}
        self._blocks_data = {}
        # {block_name: {field_name: Part}}
        self._blocks_parts = OrderedDict()
        # src_attr -> [dest_attr]
        self._listening_attrs = {}
        # (block_name, src_field_name) -> [dest_field_name]
        self._scale_offset_fields = {}
        # full_src_field -> [full_dest_field]
        self._mirrored_fields = {}
        # fields that need to inherit UNITS, SCALE and OFFSET from upstream
        self._inherit_scale = {}
        self._inherit_offset = {}
        # changes left over from last time
        self.changes = OrderedDict()
        # The PandABlock client that does the comms
        self.client = PandABlocksClient(params.hostname, params.port)
        # Filled in on reset
        self._stop_queue = None
        self._poll_spawned = None

    def do_init(self):
        # start the poll loop first to fill in our parts before calling
        # _set_block_children()
        self.start_poll_loop()
        super(PandABlocksController, self).do_reset()

    def start_poll_loop(self):
        # queue to listen for stop events
        self._stop_queue = Queue()
        if self.client.started:
            self.client.stop()
        if self.use_cothread:
            from cothread.cosocket import socket
        else:
            from socket import socket
        self.client.start(self.spawn, socket)
        if not self._blocks_parts:
            self._make_blocks_parts()
        self._poll_spawned = self.spawn(self.poll_loop)

    def do_disable(self):
        super(PandABlocksController, self).do_disable()
        self.stop_poll_loop()

    def do_reset(self):
        self.start_poll_loop()
        super(PandABlocksController, self).do_reset()

    def _poll_loop(self):
        """At 10Hz poll for changes"""
        next_poll = time.time()
        while True:
            next_poll += 0.1
            timeout = next_poll - time.time()
            if timeout < 0:
                timeout = 0
            try:
                return self._stop_queue.get(timeout=timeout)
            except TimeoutError:
                # No stop, no problem
                pass
            try:
                self.handle_changes(self.client.get_changes())
            except Exception:
                # TODO: should fault here?
                self.log_exception("Error while getting changes")

    def stop_poll_loop(self):
        if self._poll_spawned:
            self._stop_queue.put(self.STOP)
            self._poll_spawned.wait()
            self._poll_spawned = None
        if self.client.started:
            self.client.stop()

    def _make_blocks_parts(self):
        self._blocks_data = self.client.get_blocks_data()
        self._blocks_parts = OrderedDict()
        for block_name, block_data in self._blocks_data.items():
            block_names = []
            if block_data.number == 1:
                block_names.append(block_name)
            else:
                for i in range(block_data.number):
                    block_names.append("%s%d" % (block_name, i + 1))
            for bn in block_names:
                self._make_parts(bn, block_data)

    def _make_parts(self, block_name, block_data):
        mri = "%s:%s" % (self.params.mri, block_name)
        # Defer creation of parts to a block maker
        maker = PandABlocksMaker(
            self.client, block_name, block_data, self.params.areaDetectorPrefix)

        # Add in any extras we need to make from areaDetector
        parts = maker.parts.values()
        if block_name == "PCAP" and self.params.areaDetectorPrefix:
            from malcolm.includes.ADCore import adbase_parts
            parts += call_with_params(
                adbase_parts, prefix=self.params.areaDetectorPrefix)
            controller_cls = StatefulController
        else:
            controller_cls = BaseController

        # Add it to the process
        controller = call_with_params(
            controller_cls, self.process, parts, mri=mri)
        self.process.add_controller(mri, controller)

        # Store the parts so we can update them with the poller
        self._blocks_parts[block_name] = maker.parts

        # Set the initial block_url
        self._set_icon_url(block_name)

        # setup param pos on a block with pos_out to inherit SCALE OFFSET UNITS
        pos_fields = []
        pos_out_fields = []
        pos_mux_inp_fields = []
        for field_name, field_data in block_data.fields.items():
            if field_name == "INP" and field_data.field_type == "pos_mux":
                pos_mux_inp_fields.append(field_name)
            elif field_data.field_type == "pos_out":
                pos_out_fields.append(field_name)
            elif field_data.field_subtype in ("pos", "relative_pos"):
                pos_fields.append(field_name)

        # Make sure pos_fields can get SCALE from somewhere
        if pos_fields:
            sources = pos_mux_inp_fields + pos_out_fields
            assert len(sources) == 1, \
                "Expected one source of SCALE and OFFSET for %s, got %s" % (
                    pos_fields, sources)
            for field_name in pos_fields:
                self._map_scale_offset(block_name, sources[0], field_name)

        # Make the corresponding part for us
        if block_name == "PCAP" and self.params.areaDetectorPrefix:
            from malcolm.parts.pandablocks import \
                PandABlocksDriverPart as ChildPart
        elif self.params.areaDetectorPrefix:
            from malcolm.parts.pandablocks import \
                PandABlocksChildPart as ChildPart
        else:
            from malcolm.parts.builtin import ChildPart
        child_part = call_with_params(ChildPart, name=block_name, mri=mri)
        self.parts[block_name] = child_part

    def _map_scale_offset(self, block_name, src_field, dest_field):
        self._scale_offset_fields.setdefault(
            (block_name, src_field), []).append(dest_field)
        if src_field == "INP":
            # mapping based on what it is connected to, defer
            return
        for suff in ("SCALE", "OFFSET", "UNITS"):
            full_src_field = "%s.%s.%s" % (block_name, src_field, suff)
            full_dest_field = "%s.%s.%s" % (block_name, dest_field, suff)
            self._mirrored_fields.setdefault(full_src_field, []).append(
                full_dest_field)

    def _set_icon_url(self, block_name):
        icon_attr = self._blocks_parts[block_name]["icon"].attr
        fname = block_name.rstrip("0123456789")
        if fname == "LUT":
            # TODO: Get fname from func
            pass
        # TODO: make relative
        url = "http://localhost:8080/path/to/%s" % fname
        icon_attr.set_value(url)

    def handle_changes(self, changes):
        for k, v in changes.items():
            self.changes[k] = v
        for full_field, val in list(self.changes.items()):
            # If we have a mirrored field then fire off a request
            for dest_field in self._mirrored_fields.get(full_field, []):
                self.client.send("%s=%s\n" % (dest_field, val))
            block_name, field_name = full_field.split(".", 1)
            ret = self.update_attribute(block_name, field_name, val)
            if ret is not None:
                self.changes[full_field] = ret
            else:
                self.changes.pop(full_field)
            # If it was LUT.FUNC then recalculate icon
            if block_name.startswith("LUT") and field_name == "FUNC":
                self._set_icon_url(block_name)

    def update_attribute(self, block_name, field_name, val):
        ret = None
        if block_name not in self._blocks_parts:
            self.log_debug("Block %s not known", block_name)
            return
        parts = self._blocks_parts[block_name]
        if field_name not in parts:
            self.log_debug("Block %s has no field %s", block_name,
                           field_name)
            return
        part = parts[field_name]
        attr = part.attr
        field_data = self._blocks_data[block_name].fields.get(field_name, None)
        if val == Exception:
            # TODO: set error
            val = None
        elif isinstance(attr.meta, BooleanMeta):
            val = bool(int(val))
            is_bit_out = field_data and field_data.field_type == "bit_out"
            if is_bit_out and val == attr.value:
                # make bit_out things toggle while changing
                ret = val
                val = not val
        elif isinstance(attr.meta, TableMeta):
            val = part.table_from_list(val)

        # Update the value of our attribute and anyone listening
        attr.set_value(val)
        for dest_attr in self._listening_attrs.get(attr, []):
            dest_attr.set_value(val)

        # if we changed the value of a mux, update the slaved values
        if field_data and field_data.field_type in ("bit_mux", "pos_mux"):
            val_part = parts[field_name + ".VAL"]
            val_attr = val_part.attr
            self._update_val_attr(val_attr, val)
            if field_data.field_type == "pos_mux" and field_name == "INP":
                # all param pos fields should inherit scale and offset
                for dest_field_name in self._scale_offset_fields.get(
                        (block_name, field_name), []):
                    self._update_scale_offset_mapping(
                        block_name, dest_field_name, val)
        return ret

    def _update_scale_offset_mapping(self, block_name, field_name, mux_val):
        # Find the fields that depend on this input
        field_data = self._blocks_data[block_name].fields.get(field_name, None)
        if field_data.field_subtype == "relative_pos":
            suffs = ("SCALE", "UNITS")
        else:
            suffs = ("SCALE", "OFFSET", "UNITS")

        for suff in suffs:
            full_src_field = "%s.%s" % (mux_val, suff)
            full_dest_field = "%s.%s.%s" % (block_name, field_name, suff)

            # Remove mirrored fields that are already in lists
            for field_list in self._mirrored_fields.values():
                try:
                    field_list.remove(full_dest_field)
                except ValueError:
                    pass

            self._mirrored_fields.setdefault(full_src_field, []).append(
                full_dest_field)
            # update it to the right value
            if mux_val == "ZERO":
                value = dict(SCALE=1, OFFSET=0, UNITS="")[suff]
            else:
                mon_block_name, mon_field_name = mux_val.split(".", 1)
                mon_parts = self._blocks_parts[mon_block_name]
                src_attr = mon_parts["%s.%s" % (mon_field_name, suff)].attr
                value = src_attr.value
            self.client.send("%s=%s\n" % (full_dest_field, value))

    def _update_val_attr(self, val_attr, mux_val):
        # Remove the old val_attr from all lists
        for mux_list in self._listening_attrs.values():
            try:
                mux_list.remove(val_attr)
            except ValueError:
                pass
        # add it to the list of things that need to update
        if mux_val == "ZERO":
            val_attr.set_value(0)
        elif mux_val == "ONE":
            val_attr.set_value(1)
        else:
            mon_block_name, mon_field_name = mux_val.split(".", 1)
            mon_parts = self._blocks_parts[mon_block_name]
            out_attr = mon_parts[mon_field_name].attr
            self._listening_attrs.setdefault(out_attr, []).append(val_attr)
            # update it to the right value
            val_attr.set_value(out_attr.value)
