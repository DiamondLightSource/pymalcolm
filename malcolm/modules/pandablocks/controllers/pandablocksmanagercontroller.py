import time
import os
import operator
from xml.etree import cElementTree as ET

from malcolm.compat import OrderedDict, maybe_import_cothread, et_to_string
from malcolm.core import method_also_takes, Queue, TimeoutError, \
    call_with_params
from malcolm.modules.builtin.controllers import BasicController, \
    ManagerController
from malcolm.modules.builtin.parts import ChildPart
from malcolm.modules.builtin.vmetas import BooleanMeta, TableMeta, StringMeta, \
    NumberMeta
from malcolm.modules.pandablocks.parts.pandablocksmaker import \
    PandABlocksMaker, SVG_DIR
from .pandablocksclient import PandABlocksClient


LUT_CONSTANTS = dict(
    A=0xffff0000, B=0xff00ff00, C=0xf0f0f0f0, D=0xcccccccc, E=0xaaaaaaaa)


@method_also_takes(
    "hostname", StringMeta("Hostname of the box"), "localhost",
    "port", NumberMeta("uint32", "Port number of the server client"), 8888)
class PandABlocksManagerController(ManagerController):
    def __init__(self, process, parts, params):
        super(PandABlocksManagerController, self).__init__(
            process, parts, params)
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
        # lut elements to be displayed or not
        # {fnum: {id: visible}}
        self._lut_elements = {}
        # changes left over from last time
        self.changes = OrderedDict()
        # The PandABlock client that does the comms
        self.client = PandABlocksClient(params.hostname, params.port, Queue)
        # Filled in on reset
        self._stop_queue = None
        self._poll_spawned = None

    def do_init(self):
        # start the poll loop and make block parts first to fill in our parts
        # before calling _set_block_children()
        self.start_poll_loop()
        super(PandABlocksManagerController, self).do_init()

    def start_poll_loop(self):
        # queue to listen for stop events
        if not self.client.started:
            self._stop_queue = Queue()
            if self.client.started:
                self.client.stop()
            from socket import socket
            if self.use_cothread:
                cothread = maybe_import_cothread()
                if cothread:
                    from cothread.cosocket import socket
            self.client.start(self.spawn, socket)
        if not self._blocks_parts:
            self._make_blocks_parts()
        if self._poll_spawned is None:
            self._poll_spawned = self.spawn(self._poll_loop)

    def do_disable(self):
        super(PandABlocksManagerController, self).do_disable()
        self.stop_poll_loop()

    def do_reset(self):
        self.start_poll_loop()
        super(PandABlocksManagerController, self).do_reset()

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
                self.log.exception("Error while getting changes")

    def stop_poll_loop(self):
        if self._poll_spawned:
            self._stop_queue.put(None)
            self._poll_spawned.wait()
            self._poll_spawned = None
        if self.client.started:
            self.client.stop()

    def _make_blocks_parts(self):
        # {block_name_without_number: BlockData}
        self._blocks_data = OrderedDict()
        self._blocks_parts = OrderedDict()
        for block_rootname, block_data in self.client.get_blocks_data().items():
            block_names = []
            if block_data.number == 1:
                block_names.append(block_rootname)
            else:
                for i in range(block_data.number):
                    block_names.append("%s%d" % (block_rootname, i + 1))
            for block_name in block_names:
                self._blocks_data[block_name] = block_data
                self._make_parts(block_name, block_data)
        # Handle the initial set of changes to get an initial value
        self.handle_changes(self.client.get_changes())
        # Then once more to let bit_outs toggle back
        self.handle_changes({})
        assert not self.changes, "There are still changes %s" % self.changes

    def _make_child_controller(self, parts, mri):
        controller = call_with_params(
            BasicController, self.process, parts, mri=mri)
        return controller

    def _make_corresponding_part(self, block_name, mri):
        part = call_with_params(ChildPart, name=block_name, mri=mri)
        return part

    def _make_parts(self, block_name, block_data):
        mri = "%s:%s" % (self.params.mri, block_name)

        # Defer creation of parts to a block maker
        maker = PandABlocksMaker(self.client, block_name, block_data)

        # Make the child controller and add it to the process
        controller = self._make_child_controller(maker.parts.values(), mri)
        self.process.add_controller(mri, controller)

        # Store the parts so we can update them with the poller
        self._blocks_parts[block_name] = maker.parts

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
        child_part = self._make_corresponding_part(block_name, mri)
        self.add_part(child_part)

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

    def _set_lut_icon(self, block_name):
        icon_attr = self._blocks_parts[block_name]["icon"].attr
        with open(os.path.join(SVG_DIR, "LUT.svg")) as f:
            svg_text = f.read()
        fnum = int(self.client.get_field(block_name, "FUNC.RAW"))
        invis = self._get_lut_icon_elements(fnum)
        root = ET.fromstring(svg_text)
        for i in invis:
            # Find the first parent which has a child with id i
            parent = root.find('.//*[@id=%r]/..' % i)
            # Find the child and remove it
            child = parent.find('./*[@id=%r]' % i)
            parent.remove(child)
        svg_text = et_to_string(root)
        icon_attr.set_value(svg_text)

    def _get_lut_icon_elements(self, fnum):
        if not self._lut_elements:
            # Generate the lut element table
            # Do the general case funcs
            funcs = [("AND", operator.and_), ("OR", operator.or_)]
            for func, op in funcs:
                for nargs in (2, 3, 4, 5):
                    # 2**nargs permutations
                    for permutation in range(2 ** nargs):
                        self._calc_visibility(func, op, nargs, permutation)
            # Add in special cases for NOT
            for ninp in "ABCDE":
                invis = {"AND", "OR", "LUT"}
                for inp in "ABCDE":
                    if inp != ninp:
                        invis.add(inp)
                    invis.add("not%s" % inp)
                self._lut_elements[~LUT_CONSTANTS[ninp] & (2 ** 32 - 1)] = invis
            # And catchall for LUT in 0
            invis = {"AND", "OR", "NOT"}
            for inp in "ABCDE":
                invis.add("not%s" % inp)
            self._lut_elements[0] = invis
        return self._lut_elements.get(fnum, self._lut_elements[0])

    def _calc_visibility(self, func, op, nargs, permutations):
        # Visibility dictionary defaults
        invis = {"AND", "OR", "LUT", "NOT"}
        invis.remove(func)
        args = []
        for i, inp in enumerate("EDCBA"):
            # xxxxx where x is 0 or 1
            # EDCBA
            negations = format(permutations, '05b')
            if (5 - i) > nargs:
                # invisible
                invis.add(inp)
                invis.add("not%s" % inp)
            else:
                # visible
                if negations[i] == "1":
                    args.append(~LUT_CONSTANTS[inp] & (2 ** 32 - 1))
                else:
                    invis.add("not%s" % inp)
                    args.append(LUT_CONSTANTS[inp])

        # Insert into table
        fnum = op(args[0], args[1])
        for a in args[2:]:
            fnum = op(fnum, a)
        self._lut_elements[fnum] = invis

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
                self._set_lut_icon(block_name)

    def update_attribute(self, block_name, field_name, val):
        ret = None
        if block_name not in self._blocks_parts:
            self.log.debug("Block %s not known", block_name)
            return
        parts = self._blocks_parts[block_name]
        if field_name not in parts:
            self.log.debug("Block %s has no field %s", block_name, field_name)
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
            current_part = parts[field_name + ".CURRENT"]
            current_attr = current_part.attr
            self._update_current_attr(current_attr, val)
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

    def _update_current_attr(self, current_attr, mux_val):
        # Remove the old current_attr from all lists
        for mux_list in self._listening_attrs.values():
            try:
                mux_list.remove(current_attr)
            except ValueError:
                pass
        # add it to the list of things that need to update
        if mux_val == "ZERO":
            current_attr.set_value(0)
        elif mux_val == "ONE":
            current_attr.set_value(1)
        else:
            mon_block_name, mon_field_name = mux_val.split(".", 1)
            mon_parts = self._blocks_parts[mon_block_name]
            out_attr = mon_parts[mon_field_name].attr
            self._listening_attrs.setdefault(out_attr, []).append(current_attr)
            # update it to the right value
            current_attr.set_value(out_attr.value)
