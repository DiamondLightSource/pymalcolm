import time
from collections import OrderedDict

from malcolm.core import Spawnable, Loggable
from malcolm.core.vmetas import BooleanMeta, TableMeta
from malcolm.compat import queue
from malcolm.parts.pandabox.pandaboxblockmaker import PandABoxBlockMaker
from malcolm.parts.pandabox.pandaboxtablepart import PandABoxTablePart

from malcolm.controllers.defaultcontroller import DefaultController


class PandABoxPoller(Spawnable, Loggable):
    def __init__(self, process, control):
        self.set_logger_name("PandABoxPoller(%s)" % control.hostname)
        self.process = process
        self.control = control
        # block_name -> BlockData
        self._block_data = {}
        # block_name -> Block
        self._blocks = {}
        # block_name -> {field_name: Part}
        self._parts = {}
        # src_attr -> [dest_attr]
        self._listening_attrs = {}
        # (block_name, src_field_name) -> [dest_field_name]
        self._scale_offset_fields = {}
        # full_src_field -> [full_dest_field]
        self._mirrored_fields = {}
        # changes left over from last time
        self.changes = OrderedDict()
        # fields that need to inherit UNITS, SCALE and OFFSET from upstream
        self._inherit_scale = {}
        self._inherit_offset = {}
        self.q = process.create_queue()
        self.add_spawn_function(self.poll_loop,
                                self.make_default_stop_func(self.q))

    def make_panda_block(self, malcolm_name, block_name, block_data):
        # Validate and store block_data
        self._store_block_data(block_name, block_data)

        # Defer creation of parts to a block maker
        maker = PandABoxBlockMaker(self.process, self.control, block_name,
                                   block_data)

        # Make a controller
        controller = DefaultController(malcolm_name, self.process, maker.parts)
        block = controller.block

        self._blocks[block_name] = block
        self._parts[block_name] = maker.parts

        # Set the initial block_url
        self._set_icon_url(block_name)

        return block

    def _set_icon_url(self, block_name):
        icon_attr = self._blocks[block_name]["ICON"]
        fname = block_name.rstrip("0123456789")
        if fname == "LUT":
            # TODO: Get fname from func
            pass
        # TODO: make relative
        url = "http://localhost:8080/path/to/%s" % fname
        icon_attr.set_value(url)

    def _store_block_data(self, block_name, block_data):
        self._block_data[block_name] = block_data

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

    def poll_loop(self):
        """At 10Hz poll for changes"""
        next_poll = time.time()
        while True:
            next_poll += 0.1
            timeout = next_poll - time.time()
            if timeout < 0:
                timeout = 0
            try:
                message = self.q.get(timeout=timeout)
                if message is Spawnable.STOP:
                    break
            except queue.Empty:
                # No problem
                pass
            try:
                self.handle_changes(self.control.get_changes())
            except Exception:
                self.log_exception("Error while getting changes")

    def handle_changes(self, changes):
        self.changes.update(changes)
        for full_field, val in list(self.changes.items()):
            # If we have a mirrored field then fire off a request
            for dest_field in self._mirrored_fields.get(full_field, []):
                self.control.send("%s=%s\n" % (dest_field, val))
            block_name, field_name = full_field.split(".", 1)
            attr_name = field_name.replace(".", "_")
            ret = self.update_attribute(block_name, attr_name, val)
            if ret is not None:
                self.changes[full_field] = ret
            else:
                self.changes.pop(full_field)
            # If it was LUT.FUNC then recalculate icon
            if block_name.startswith("LUT") and attr_name == "FUNC":
                self._set_icon_url(block_name)

    def update_attribute(self, block_name, attr_name, val):
        ret = None
        if block_name not in self._blocks:
            self.log_debug("Block %s not known", block_name)
            return
        block = self._blocks[block_name]
        if attr_name not in block:
            self.log_debug("Block %s has no attribute %s", block_name,
                           attr_name)
            return
        attr = block[attr_name]
        field_data = self._block_data[block_name].fields.get(attr_name, None)
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
            table_part = self._parts[block_name][attr_name]
            val = table_part.table_from_list(val)

        # Update the value of our attribute and anyone listening
        attr.set_value(val)
        for dest_attr in self._listening_attrs.get(attr, []):
            dest_attr.set_value(val)

        # if we changed the value of a mux, update the slaved values
        if field_data and field_data.field_type in ("bit_mux", "pos_mux"):
            val_attr = block[attr_name + "_VAL"]
            self._update_val_attr(val_attr, val)
            if field_data.field_type == "pos_mux" and attr_name == "INP":
                # all param pos fields should inherit scale and offset
                for dest_field_name in self._scale_offset_fields.get(
                        (block_name, attr_name), []):
                    self._update_scale_offset_mapping(
                        block_name, dest_field_name, val)
        return ret

    def _update_scale_offset_mapping(self, block_name, field_name, mux_val):
        # Find the fields that depend on this input
        field_data = self._block_data[block_name].fields.get(field_name, None)
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
                mon_block = self._blocks[mon_block_name]
                src_attr = mon_block["%s_%s" % (mon_field_name, suff)]
                value = src_attr.value
            self.control.send("%s=%s\n" % (full_dest_field, value))

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
            mon_block = self._blocks[mon_block_name]
            out_attr = mon_block[mon_field_name]
            self._listening_attrs.setdefault(out_attr, []).append(val_attr)
            # update it to the right value
            val_attr.set_value(out_attr.value)