import os

from malcolm.compat import OrderedDict
from malcolm.core import call_with_params
from malcolm.modules.builtin.parts import GroupPart, IconPart, LabelPart
from malcolm.tags import widget, group, inport, outport, config
from malcolm.modules.builtin.vmetas import BooleanMeta, NumberMeta, StringMeta, \
    ChoiceMeta, TableMeta
from .pandablocksactionpart import PandABlocksActionPart
from .pandablocksfieldpart import PandABlocksFieldPart
from .pandablockstablepart import PandABlocksTablePart


SVG_DIR = os.path.join(os.path.dirname(__file__), "..", "icons")


def make_meta(subtyp, description, tags, writeable=True, labels=None):
    if subtyp == "enum":
        if writeable:
            widget_type = "combo"
        else:
            widget_type = "textupdate"
        tags.append(widget(widget_type))
        meta = ChoiceMeta(description, labels, tags)
    elif subtyp == "bit":
        if writeable:
            widget_type = "checkbox"
        else:
            widget_type = "led"
        tags.append(widget(widget_type))
        meta = BooleanMeta(description, tags)
    else:
        if writeable:
            widget_type = "textinput"
        else:
            widget_type = "textupdate"
        tags.append(widget(widget_type))
        if subtyp == "uint":
            meta = NumberMeta("uint32", description, tags)
        elif subtyp == "int":
            meta = NumberMeta("int32", description, tags)
        elif subtyp == "scalar":
            meta = NumberMeta("float64", description, tags)
        elif subtyp == "lut":
            meta = StringMeta(description, tags)
        elif subtyp in ("pos", "relative_pos"):
            meta = NumberMeta("float64", description, tags)
        else:
            raise ValueError("Unknown subtype %r" % subtyp)
    return meta


class PandABlocksMaker(object):
    def __init__(self, client, block_name, block_data):
        self.client = client
        self.block_name = block_name
        self.block_data = block_data
        self.parts = OrderedDict()
        # Make an icon
        self._make_icon_label()
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
            if subtyp != "adc":
                self._make_data_delay(field_name)
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

    def _make_icon_label(self):
        block_type = self.block_name.rstrip("0123456789")
        svg_name = block_type + ".svg"
        part = call_with_params(IconPart, svg=os.path.join(SVG_DIR, svg_name))
        self._add_part("icon", part)
        part = call_with_params(LabelPart, initialValue=block_type)
        self._add_part("label", part)

    def _make_scale_offset(self, field_name):
        group_tag = self._make_group("outputs")
        meta = StringMeta("Units for position fields on this block",
                          tags=[group_tag, widget("textinput")])
        self._make_field_part(field_name + ".UNITS", meta, writeable=True)
        meta = NumberMeta("float64", "Scale for block position fields",
                          tags=[group_tag, widget("textinput")])
        self._make_field_part(field_name + ".SCALE", meta, writeable=True)
        meta = NumberMeta("float64", "Offset for block position fields",
                          tags=[group_tag, widget("textinput")])
        self._make_field_part(field_name + ".OFFSET", meta, writeable=True)

    def _make_time_parts(self, field_name, field_data, writeable):
        description = field_data.description
        if writeable:
            widget_tag = widget("textupdate")
            group_tag = self._make_group("parameters")
        else:
            widget_tag = widget("textinput")
            group_tag = self._make_group("readbacks")
        meta = NumberMeta("float64", description, [group_tag, widget_tag])
        self._make_field_part(field_name, meta, writeable)
        meta = ChoiceMeta(description + " time units", ["s", "ms", "us"],
                          tags=[group_tag, widget("combo")])
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
            arg_meta = None
        else:
            arg_meta = make_meta(
                field_data.field_subtype, field_data.description,
                tags=[group_tag], writeable=True, labels=field_data.labels)
        part = PandABlocksActionPart(
            self.client, self.block_name, field_name,
            field_data.description, [group_tag], arg_meta)
        self._add_part(field_name, part)

    def _make_out(self, field_name, field_data, typ):
        group_tag = self._make_group("outputs")
        if typ == "bit":
            outport_type = "bool"
        else:
            outport_type = "int32"
        flow_tag = outport(
            outport_type, "%s.%s" % (self.block_name, field_name))
        meta = make_meta(typ, field_data.description,
                         tags=[group_tag, flow_tag], writeable=False)
        self._make_field_part(field_name, meta, writeable=False)

    def _make_data_delay(self, field_name):
        group_tag = self._make_group("outputs")
        meta = NumberMeta(
            "uint8", "How many FPGA ticks to delay data capture",
            tags=[group_tag, widget("textinput")])
        self._make_field_part(field_name + ".DATA_DELAY", meta, writeable=True)

    def _make_out_capture(self, field_name, field_data):
        group_tag = self._make_group("outputs")
        meta = ChoiceMeta("Capture %s in PCAP?" % field_name,
                          field_data.labels, tags=[group_tag, widget("combo")])
        self._make_field_part(field_name + ".CAPTURE", meta, writeable=True)

    def _make_mux(self, field_name, field_data, typ):
        group_tag = self._make_group("inputs")
        if typ == "bit":
            inport_type = "bool"
        else:
            inport_type = "int32"
        meta = ChoiceMeta(field_data.description, field_data.labels, tags=[
            group_tag, inport(inport_type, "ZERO"), widget("combo")])
        self._make_field_part(field_name, meta, writeable=True)
        meta = make_meta(typ, "%s current value" % field_name,
                         tags=[group_tag], writeable=False)
        self._make_field_part(field_name + ".CURRENT", meta, writeable=False)

    def _make_mux_delay(self, field_name):
        group_tag = self._make_group("inputs")
        meta = NumberMeta(
            "uint8", "How many FPGA ticks to delay input",
            tags=[group_tag, widget("textinput")])
        self._make_field_part(field_name + ".DELAY", meta, writeable=True)

    def _make_table(self, field_name, field_data):
        group_tag = self._make_group("parameters")
        tags = [widget("table"), group_tag, config()]
        meta = TableMeta(field_data.description, tags)
        part = PandABlocksTablePart(self.client, meta,
                                    self.block_name, field_name, writeable=True)
        self._add_part(field_name, part)

    def _add_part(self, field_name, part):
        assert field_name not in self.parts, \
            "Already have a field %r" % field_name
        self.parts[field_name] = part

    def _make_field_part(self, field_name, meta, writeable, initial_value=None):
        if writeable:
            meta.set_tags(meta.tags + (config(),))
        part = PandABlocksFieldPart(self.client, meta,
                                    self.block_name, field_name, writeable,
                                    initial_value)
        self._add_part(field_name, part)

    def _make_group(self, attr_name):
        if attr_name not in self.parts:
            part = call_with_params(
                GroupPart, name=attr_name,
                description="All %s attributes" % attr_name)
            self._add_part(attr_name, part)
        group_tag = group(attr_name)
        return group_tag
