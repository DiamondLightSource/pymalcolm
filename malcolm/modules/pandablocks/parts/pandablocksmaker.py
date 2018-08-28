import os

from malcolm.compat import OrderedDict
from malcolm.modules.builtin.parts import GroupPart, IconPart, TitlePart
from malcolm.core import Widget, group_tag, Port, config_tag, \
    BooleanMeta, ChoiceMeta, NumberMeta, StringMeta, TableMeta
from .pandablocksactionpart import PandABlocksActionPart
from .pandablocksfieldpart import PandABlocksFieldPart
from .pandablockstablepart import PandABlocksTablePart


SVG_DIR = os.path.join(os.path.dirname(__file__), "..", "icons")


def make_meta(subtyp, description, tags, writeable=True, labels=None):
    if subtyp == "enum":
        meta = ChoiceMeta(description, labels)
    elif subtyp == "bit":
        meta = BooleanMeta(description)
    elif subtyp in ("uint", ""):
        meta = NumberMeta("uint32", description)
    elif subtyp in ("int", "pos"):
        meta = NumberMeta("int32", description)
    elif subtyp in ("scalar", "xadc"):
        meta = NumberMeta("float64", description)
    elif subtyp == "lut":
        meta = StringMeta(description)
    else:
        raise ValueError("Unknown subtype %r" % subtyp)
    meta.set_writeable(writeable)
    tags.append(meta.default_widget().tag())
    meta.set_tags(tags)
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

        if typ in ("read", "xadc"):
            writeable = False
        else:
            writeable = True

        if typ == "time" or typ in ("param", "read") and subtyp == "time":
            self._make_time_parts(field_name, field_data, writeable)
        elif typ == "write" and subtyp == "action":
            self._make_action_part(field_name, field_data)
        elif typ in ("param", "read", "write", "xadc"):
            self._make_param_part(field_name, field_data, writeable)
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
            raise ValueError("Unknown type %r subtype %r" % (typ, subtyp))

    def _make_icon_label(self):
        block_type = self.block_name.rstrip("0123456789")
        svg_name = block_type + ".svg"
        part = IconPart(svg=os.path.join(SVG_DIR, svg_name))
        self._add_part("icon", part)
        label = self.block_data.description + " " + \
            self.block_name[len(block_type):]
        part = TitlePart(value=label)
        self._add_part("label", part)

    def _make_scale_offset(self, field_name):
        group = self._make_group("outputs")
        meta = StringMeta("Units for position fields on this block",
                          tags=[group, Widget.TEXTINPUT.tag()])
        self._make_field_part(field_name + ".UNITS", meta, writeable=True)
        meta = NumberMeta("float64", "Scale for block position fields",
                          tags=[group, Widget.TEXTINPUT.tag()])
        self._make_field_part(field_name + ".SCALE", meta, writeable=True)
        meta = NumberMeta("float64", "Offset for block position fields",
                          tags=[group, Widget.TEXTINPUT.tag()])
        self._make_field_part(field_name + ".OFFSET", meta, writeable=True)
        meta = NumberMeta("float64", "Current scaled value of position field",
                          tags=[group, Widget.TEXTUPDATE.tag()])
        self._make_field_part(field_name + ".SCALED", meta, writeable=False)

    def _make_time_parts(self, field_name, field_data, writeable):
        description = field_data.description
        if writeable:
            widget = Widget.TEXTINPUT
            group = self._make_group("parameters")
        else:
            widget = Widget.TEXTUPDATE
            group = self._make_group("readbacks")
        meta = NumberMeta("float64", description, [group, widget.tag()])
        # We must change time units before value, so restore value in 2nd
        # iteration
        self._make_field_part(field_name, meta, writeable, iteration=2)
        meta = ChoiceMeta(description + " time units", ["s", "ms", "us"],
                          tags=[group, Widget.COMBO.tag()])
        self._make_field_part(field_name + ".UNITS", meta, writeable=True)

    def _make_param_part(self, field_name, field_data, writeable):
        if writeable:
            group = self._make_group("parameters")
        else:
            group = self._make_group("readbacks")
        if field_data.field_type == "xadc":
            subtype = "xadc"
        else:
            subtype = field_data.field_subtype
        meta = make_meta(subtype, field_data.description,
                         [group], writeable, field_data.labels)
        self._make_field_part(field_name, meta, writeable)

    def _make_action_part(self, field_name, field_data):
        group = self._make_group("parameters")
        part = PandABlocksActionPart(
            self.client, self.block_name, field_name,
            field_data.description, [group])
        self._add_part(field_name, part)

    def _make_out(self, field_name, field_data, typ):
        group = self._make_group("outputs")
        if typ == "bit":
            port_type = Port.BOOL
        else:
            port_type = Port.INT32
        flow_tag = port_type.source_port_tag(
            "%s.%s" % (self.block_name, field_name))
        meta = make_meta(typ, field_data.description,
                         tags=[group, flow_tag], writeable=False)
        self._make_field_part(field_name, meta, writeable=False)

    def _make_out_capture(self, field_name, field_data):
        group = self._make_group("outputs")
        meta = ChoiceMeta("Capture %s in PCAP?" % field_name,
                          field_data.labels, tags=[group, Widget.COMBO.tag()])
        self._make_field_part(field_name + ".CAPTURE", meta, writeable=True)

    def _make_mux(self, field_name, field_data, typ):
        group = self._make_group("inputs")
        if typ == "bit":
            port_type = Port.BOOL
        else:
            port_type = Port.INT32
        labels = [x for x in field_data.labels if x in ("ZERO", "ONE")] + \
            sorted(x for x in field_data.labels if x not in ("ZERO", "ONE"))
        meta = ChoiceMeta(field_data.description, labels, tags=[
            group, port_type.sink_port_tag("ZERO"),
            Widget.COMBO.tag()])
        self._make_field_part(field_name, meta, writeable=True)
        meta = make_meta(typ, "%s current value" % field_name,
                         tags=[group], writeable=False)
        self._make_field_part(field_name + ".CURRENT", meta, writeable=False)

    def _make_mux_delay(self, field_name):
        group = self._make_group("inputs")
        meta = NumberMeta(
            "uint8", "How many FPGA ticks to delay input",
            tags=[group, Widget.TEXTINPUT.tag()])
        self._make_field_part(field_name + ".DELAY", meta, writeable=True)

    def _make_table(self, field_name, field_data):
        group = self._make_group("parameters")
        tags = [Widget.TABLE.tag(), group, config_tag()]
        meta = TableMeta(field_data.description, tags, writeable=True)
        part = PandABlocksTablePart(self.client, meta,
                                    self.block_name, field_name)
        self._add_part(field_name, part)

    def _add_part(self, field_name, part):
        assert field_name not in self.parts, \
            "Already have a field %r" % field_name
        self.parts[field_name] = part

    def _make_field_part(self, field_name, meta, writeable, initial_value=None,
                         iteration=1):
        if writeable:
            meta.set_tags(list(meta.tags) + [config_tag(iteration)])
            meta.set_writeable(True)
        part = PandABlocksFieldPart(self.client, meta,
                                    self.block_name, field_name, initial_value)
        self._add_part(field_name, part)

    def _make_group(self, attr_name):
        if attr_name not in self.parts:
            part = GroupPart(attr_name, "All %s attributes" % attr_name)
            self._add_part(attr_name, part)
        group = group_tag(attr_name)
        return group
