from collections import OrderedDict

from malcolm.core import Loggable
from malcolm.core.vmetas import BooleanMeta, NumberMeta, StringMeta, \
    ChoiceMeta, TableMeta
from malcolm.parts.pandabox.pandaboxfieldpart import PandABoxFieldPart
from malcolm.parts.pandabox.pandaboxgrouppart import PandABoxGroupPart
from malcolm.parts.pandabox.pandaboxtablepart import PandABoxTablePart
from malcolm.parts.pandabox.pandaboxactionpart import PandABoxActionPart


def make_meta(subtyp, description, tags, writeable=True, labels=None):
    if writeable:
        widget = "widget:textinput"
    else:
        widget = "widget:textupdate"
    if subtyp == "uint":
        meta = NumberMeta("uint32", description, tags + [widget])
    elif subtyp == "int":
        meta = NumberMeta("int32", description, tags + [widget])
    elif subtyp == "scalar":
        meta = NumberMeta("float64", description, tags + [widget])
    elif subtyp == "bit":
        if writeable:
            widget = "widget:toggle"
        else:
            widget = "widget:led"
        meta = BooleanMeta(description, tags + [widget])
    elif subtyp == "lut":
        meta = StringMeta(description, tags + [widget])
    elif subtyp == "enum":
        meta = ChoiceMeta(description, labels, tags + ["widget:combo"])
    elif subtyp in ("pos", "relative_pos"):
        meta = NumberMeta("float64", description, tags + [widget])
    else:
        raise ValueError("Unknown subtype %r" % subtyp)
    return meta


class PandABoxBlockMaker(Loggable):
    def __init__(self, process, control, block_name, block_data):
        self.set_logger_name("PandABoxBlockMaker")
        self.process = process
        self.control = control
        self.block_name = block_name
        self.block_data = block_data
        self.parts = OrderedDict()
        # Make an icon
        self._make_icon()
        for field_name, field_data in block_data.fields.items():
            self.make_parts_for(field_name, field_data)

    def make_parts_for(self, field_name, field_data):
        """Create the relevant parts for this field

        Args:
            field_name (str): Short field name, e.g. VAL
            field_data (FieldData): Field data object
        """
        typ = field_data.field_type
        subtyp = field_data.field_subtype

        if typ == "read":
            writeable = False
        else:
            writeable = True

        if typ == "time" or typ in ("param", "read") and subtyp == "time":
            self._make_time_parts(field_name, field_data, writeable)
        elif typ in ("param", "read"):
            self._make_param_part(field_name, field_data, writeable)
        elif typ == "write":
            self._make_action_part(field_name, field_data)
        elif typ == "bit_out":
            self._make_out(field_name, field_data, "bit")
        elif typ == "pos_out":
            self._make_out(field_name, field_data, "pos")
            self._make_scale_offset(field_name)
            self._make_out_capture(field_name, field_data)
        elif typ == "ext_out":
            self._make_out_capture(field_name, field_data)
        elif typ == "bit_mux":
            self._make_mux(field_name, field_data, "bit")
            self._make_mux_delay(field_name)
        elif typ == "pos_mux":
            self._make_mux(field_name, field_data, "pos")
        elif typ == "table":
            self._make_table(field_name, field_data)
        else:
            raise ValueError("Unknown type %r subtype %r" % (type, subtyp))

    def _make_icon(self):
        # TODO: fix to be relative when we are hosting web gui
        meta = StringMeta("URL for ICON", tags=["flowgraph:icon"])
        self._make_field_part("ICON", meta, writeable=False)

    def _make_scale_offset(self, field_name):
        group_tag = self._make_group("outputs")
        meta = StringMeta("Units for position fields on this block",
                          tags=[group_tag, "widget:textinput"])
        self._make_field_part(field_name + ".UNITS", meta, writeable=True)
        meta = NumberMeta("float64", "Scale for block position fields",
                          tags=[group_tag, "widget:textinput"])
        self._make_field_part(field_name + ".SCALE", meta, writeable=True)
        meta = NumberMeta("float64", "Offset for block position fields",
                          tags=[group_tag, "widget:textinput"])
        self._make_field_part(field_name + ".OFFSET", meta, writeable=True)

    def _make_time_parts(self, field_name, field_data, writeable):
        description = field_data.description
        if writeable:
            widget_tag = "widget:textupdate"
            group_tag = self._make_group("parameters")
        else:
            widget_tag = "widget:textinput"
            group_tag = self._make_group("readbacks")
        meta = NumberMeta("float64", description, [group_tag, widget_tag])
        self._make_field_part(field_name, meta, writeable)
        meta = ChoiceMeta(description + " time units", ["s", "ms", "us"],
                          tags=[group_tag, "widget:combo"])
        self._make_field_part(field_name + ".UNITS", meta, writeable=True)

    def _make_param_part(self, field_name, field_data, writeable):
        if writeable:
            group_tag = self._make_group("parameters")
        else:
            group_tag = self._make_group("readbacks")
        meta = make_meta(field_data.field_subtype, field_data.description,
                         [group_tag], writeable, field_data.labels)
        self._make_field_part(field_name, meta, writeable)

    def _make_action_part(self, field_name, field_data):
        group_tag = self._make_group("actions")
        if field_data.field_subtype == "action":
            # Nothing to send
            arg_name = None
            arg_meta = None
        else:
            arg_name = field_name
            arg_meta = make_meta(
                field_data.field_subtype, field_data.description,
                tags=[group_tag], writeable=True, labels=field_data.labels)
        part = PandABoxActionPart(
            self.process, self.control, self.block_name, field_name,
            field_data.description, ["widget:action", group_tag], arg_name,
            arg_meta)
        self._add_part(field_name, part)

    def _make_out(self, field_name, field_data, typ):
        group_tag = self._make_group("outputs")
        flow_tag = "flowgraph:outport:%s:%s.%s" % (
            typ, self.block_name, field_name)
        meta = make_meta(typ, field_data.description,
                         tags=[group_tag, flow_tag], writeable=False)
        self._make_field_part(field_name, meta, writeable=False)

    def _make_out_capture(self, field_name, field_data):
        group_tag = self._make_group("outputs")
        meta = ChoiceMeta("Capture %s in PCAP?" % field_name,
                          field_data.labels, tags=[group_tag, "widget:combo"])
        self._make_field_part(field_name + ".CAPTURE", meta, writeable=True)
        meta = NumberMeta(
            "uint8", "How many FPGA ticks to delay data capture",
            tags=[group_tag, "widget:textinput"])
        self._make_field_part(field_name + ".DATA_DELAY", meta, writeable=True)

    def _make_mux(self, field_name, field_data, typ):
        group_tag = self._make_group("inputs")
        meta = ChoiceMeta(field_data.description, field_data.labels,
                          tags=[group_tag, "flowgraph:inport:%s" % typ,
                                "widget:combo"])
        self._make_field_part(field_name, meta, writeable=True)
        meta = make_meta(typ, "%s current value" % field_name,
                         tags=[group_tag], writeable=False)
        self._make_field_part(field_name + ".VAL", meta, writeable=False)

    def _make_mux_delay(self, field_name):
        group_tag = self._make_group("inputs")
        meta = NumberMeta(
            "uint8", "How many FPGA ticks to delay input",
            tags=[group_tag, "widget:textinput"])
        self._make_field_part(field_name + ".DELAY", meta, writeable=True)

    def _make_table(self, field_name, field_data):
        widget_tag = "widget:table"
        group_tag = self._make_group("parameters")
        meta = TableMeta(field_data.description, [widget_tag, group_tag])
        part = PandABoxTablePart(self.process, self.control, meta,
                                 self.block_name, field_name, writeable=True)
        self._add_part(field_name, part)

    def _add_part(self, field_name, part):
        assert field_name not in self.parts, \
            "Already have a field %r" % field_name
        self.parts[field_name] = part

    def _make_field_part(self, field_name, meta, writeable, initial_value=None):
        part = PandABoxFieldPart(self.process, self.control, meta,
                                 self.block_name, field_name, writeable,
                                 initial_value)
        self._add_part(field_name, part)

    def _make_group(self, attr_name):
        if attr_name not in self.parts:
            part = PandABoxGroupPart(self.process, attr_name)
            self._add_part(attr_name, part)
        group_tag = "group:%s" % attr_name
        return group_tag
