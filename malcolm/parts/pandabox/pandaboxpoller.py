import time

from malcolm.core import Spawnable, Loggable
from malcolm.compat import queue
from malcolm.parts.pandabox.pandaboxblockmaker import PandABoxBlockMaker

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
        # (block, field) -> [list of .VAL attributes that need updating]
        self._muxes = {}
        # changes left over from last time
        self.changes = {}
        # fields that need to inherit UNITS, SCALE and OFFSET from upstream
        self._inherit_scale = {}
        self._inherit_offset = {}
        self.q = process.create_queue()
        self.add_spawn_function(self.poll_loop,
                                self.make_default_stop_func(self.q))

    def make_panda_block(self, malcolm_name, block_name, block_data):
        self._block_data[block_name] = block_data

        # Defer creation of parts to a block maker
        maker = PandABoxBlockMaker(self.process, self.control, block_name,
                                   block_data)

        # Make a controller
        controller = DefaultController(malcolm_name, self.process, maker.parts)
        block = controller.block

        self._blocks[block_name] = block

        return block

    def poll_loop(self):
        """At 10Hz poll for changes"""
        next_poll = time.time()
        while True:
            next_poll += 0.1
            try:
                message = self.q.get(timeout=next_poll - time.time())
                if message is Spawnable.STOP:
                    break
            except queue.Empty:
                # No problem
                pass
            self.changes.update(self.control.get_changes())
            for full_field, val in self.changes.items():
                block_name, field_name = full_field.split(".", 1)
                assert block_name in self._blocks, \
                    "Block {} not known".format(block_name)
                field_name = field_name.replace(".", ":")
                ret = self.update_attribute(block_name, field_name, val)
                if ret is not None:
                    self.changes[full_field] = ret
                else:
                    self.changes.pop(full_field)

    def update_attribute(self, block_name, field_name, val):
        ret = None
        assert field_name in block_name.attributes, \
            "Block {} has no attribute {}".format(block_name.name, field_name)
        attr = block_name.attributes[field_name]
        if val == Exception:
            # set error
            alarm = Alarm(AlarmSeverity.majorAlarm, AlarmStatus.Calc,
                          "Not in range")
            attr.update(alarm=alarm)
        else:
            if isinstance(attr.typ, VBool):
                val = bool(int(val))
                if field_name in block_name.field_data and \
                                block_name.field_data[field_name][0] == "bit_out" and \
                                val == attr.value:
                    # make bit_out things toggle while changing
                    ret = val
                    val = not val
            attr.update(val)
            for listen_block, mux_field in self._muxes.get((block_name, field_name), []):
                val_attr = listen_block.attributes[mux_field + ":VAL"]
                val_attr.update(val)
        # if we changed the value of a pos_mux or bit_mux, update its value
        if field_name in block_name.field_data and \
                        block_name.field_data[field_name][0] in ("bit_mux", "pos_mux"):
            # this is the attribute that needs to update
            for mux_list in self._muxes.values():
                try:
                    mux_list.remove((block_name, field_name))
                except ValueError:
                    pass
            # add it to the list of things that need to update
            mon_block_name, mon_field = val.split(".", 1)
            mon_block = self._blocks[mon_block_name]
            self._muxes.setdefault((mon_block, mon_field), []).append(
                (block_name, field_name))
            # update it to the right value
            val_attr = block_name.attributes[field_name + ":VAL"]
            val_attr.update(mon_block.attributes[mon_field].value)
            # make sure it's visible
            if mon_field != "ZERO" and block_name.VISIBLE != "Show":
                block_name._set_visible("Show")
        return ret

