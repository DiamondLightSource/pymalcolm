import os

from annotypes import Anno, TYPE_CHECKING

from malcolm.core import AMri, Widget, group_tag, NumberMeta, ChoiceMeta, \
    config_tag, BooleanMeta, StringMeta, Port, TableMeta, TimeStamp, \
    without_linked_value_tags, linked_value_tag, VMeta, snake_to_camel
from malcolm.modules import builtin
from ..parts.pandaiconpart import PandAIconPart
from ..parts.pandalabelpart import PandALabelPart
from ..parts.pandaluticonpart import PandALutIconPart
from ..parts.pandaactionpart import PandAActionPart
from ..parts.pandafieldpart import PandAFieldPart
from ..parts.pandatablepart import PandATablePart
from ..util import SVG_DIR, AClient, ADocUrlBase, ABlockName
from ..pandablocksclient import BlockData, FieldData

if TYPE_CHECKING:
    from typing import Dict, Any, Optional, Union
    ChangeHandler = Union[PandAFieldPart, PandALabelPart]


with Anno("Prefix to put on the beginning of the Block Name to make MRI"):
    AMriPrefix = str
with Anno("The BlockData object showing the fields of the Block"):
    ABlockData = BlockData

# Pull re-used annotypes into our namespace in case we are subclassed
AClient = AClient
ADocUrlBase = ADocUrlBase
ABlockName = ABlockName


def make_meta(subtyp, description, tags, writeable=True, labels=None):
    if subtyp == "enum":
        meta = ChoiceMeta(description, labels)
    elif subtyp == "bit":
        meta = BooleanMeta(description)
    elif subtyp in ("uint", ""):
        meta = NumberMeta("uint32", description)
    elif subtyp in ("int", "pos"):
        meta = NumberMeta("int32", description)
    elif subtyp == "scalar":
        meta = NumberMeta("float64", description)
    elif subtyp == "lut":
        meta = StringMeta(description)
    else:
        raise ValueError("Unknown subtype %r" % subtyp)
    meta.set_writeable(writeable)
    tags.append(meta.default_widget().tag())
    meta.set_tags(tags)
    return meta


class PandABlockController(builtin.controllers.BasicController):
    def __init__(self,
                 client,  # type: AClient
                 mri_prefix,  # type: AMri
                 block_name,  # type: ABlockName
                 block_data,  # type: ABlockData
                 doc_url_base,  # type: ADocUrlBase
                 ):
        # type: (...) -> None
        super(PandABlockController, self).__init__(
            mri="%s:%s" % (mri_prefix, block_name))
        # Store
        self.client = client
        self.mri_prefix = mri_prefix
        self.block_name = block_name
        self.block_data = block_data
        self.doc_url_base = doc_url_base
        # {field_name: part}
        self.field_parts = {}  # type: Dict[str, Optional[ChangeHandler]]
        # {field_name: attr.meta}
        self.mux_metas = {}  # type: Dict[str, VMeta]
        # Make an icon, label and help for the Block
        self.icon_part = self._make_common_parts()  # type: PandAIconPart
        # Create parts for each field
        for field_name, field_data in block_data.fields.items():
            self._make_parts_for(field_name, field_data)

    def handle_changes(self, changes, ts):
        # type: (Dict[str, Any], TimeStamp) -> None
        with self.changes_squashed:
            icon_needs_update = False
            for k, v in changes.items():
                # Work out if there is a part we need to notify
                try:
                    part = self.field_parts[k]
                except KeyError:
                    self.log.exception(
                        "Can't handle field %s.%s" % (self.block_name, k))
                    part = None
                if part is None:
                    continue
                part.handle_change(v, ts)
                if not icon_needs_update:
                    icon_needs_update = k in self.icon_part.update_fields
                try:
                    mux_meta = self.mux_metas[k]
                except KeyError:
                    pass
                else:
                    self._handle_mux_update(mux_meta, v)
            if icon_needs_update:
                d = {k: self.field_parts[k].attr.value
                     for k in self.icon_part.update_fields}
                self.icon_part.update_icon(d, ts)

    def _handle_mux_update(self, mux_meta, v):
        # Mux changed its value, update its link to a different
        # Attribute
        tags = without_linked_value_tags(mux_meta.tags)
        split = v.split(".")
        if len(split) == 2:
            block_name, field_name = split
            attr_name = snake_to_camel(field_name.replace(".", "_"))
            block_mri = "%s:%s" % (self.mri_prefix, block_name)
            tags.append(linked_value_tag(block_mri, attr_name))
        mux_meta.set_tags(tags)

    def _make_common_parts(self):
        # type: () -> PandAIconPart
        block_type = self.block_name.rstrip("0123456789")
        block_number = self.block_name[len(block_type):]
        svg_path = os.path.join(SVG_DIR, block_type + ".svg")
        if block_type == "LUT":
            icon_cls = PandALutIconPart
        else:
            icon_cls = PandAIconPart
        icon_part = icon_cls(self.client, self.block_name, svg_path)
        self.add_part(icon_part)
        label = self.block_data.description
        metadata_field = "LABEL_%s" % self.block_name
        if block_number:
            # If we have multiple blocks, make the labels unique
            label += " %s" % block_number
        else:
            # If we only have one block, the metadata field still has numbers
            metadata_field += "1"
        label_part = PandALabelPart(self.client, metadata_field, value=label)
        self.add_part(label_part)
        self.field_parts["LABEL"] = label_part
        self.add_part(builtin.parts.HelpPart("%s/build/%s_doc.html" % (
            self.doc_url_base, block_type.lower())))
        return icon_part

    def _make_parts_for(self, field_name, field_data):
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
            self._make_time(field_name, field_data, writeable)
        elif typ == "write" and subtyp == "action":
            self._make_action(field_name, field_data)
        elif typ in ("param", "read", "write"):
            self._make_param(field_name, field_data, writeable)
        elif typ == "bit_out":
            self._make_out(field_name, field_data, "bit")
        elif typ == "pos_out":
            self._make_out(field_name, field_data, "pos")
            # Some attributes are handled by the top level busses table
            # so mark as present but ignored
            for suffix in ("CAPTURE", "UNITS", "SCALE", "OFFSET", "DATA_DELAY"):
                self.field_parts["%s.%s" % (field_name, suffix)] = None
        elif typ == "ext_out":
            if subtyp == "bits":
                # Bits is handled by the top level table, so mark it as being
                # present, but ignored
                self.field_parts[field_name + ".CAPTURE"] = None
            else:
                self._make_ext_capture(field_name, field_data)
        elif typ == "bit_mux":
            self._make_mux(field_name, field_data, Port.BOOL)
            self._make_mux_delay(field_name)
        elif typ == "pos_mux":
            self._make_mux(field_name, field_data, Port.INT32)
        elif typ == "table":
            self._make_table(field_name, field_data)
        else:
            raise ValueError("Unknown type %r subtype %r" % (typ, subtyp))

    def _make_group(self, attr_name):
        # type: (str) -> str
        if attr_name not in self.parts:
            self.add_part(builtin.parts.GroupPart(
                attr_name, "All %s attributes" % attr_name))
        group = group_tag(attr_name)
        return group

    def _make_field_part(self, field_name, meta, writeable, initial_value=None,
                         iteration=1):
        if writeable:
            meta.set_tags(list(meta.tags) + [config_tag(iteration)])
            meta.set_writeable(True)
        part = PandAFieldPart(
            self.client, meta, self.block_name, field_name, initial_value)
        self.add_part(part)
        self.field_parts[field_name] = part

    def _make_time(self, field_name, field_data, writeable):
        # type: (str, FieldData, bool) -> None
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

    def _make_action(self, field_name, field_data):
        # type: (str, FieldData) -> None
        group = self._make_group("parameters")
        self.add_part(PandAActionPart(
            self.client, self.block_name, field_name,
            field_data.description, [group]))

    def _make_param(self, field_name, field_data, writeable):
        # type: (str, FieldData, bool) -> None
        if writeable:
            group = self._make_group("parameters")
        else:
            group = self._make_group("readbacks")
        meta = make_meta(field_data.field_subtype, field_data.description,
                         [group], writeable, field_data.labels)
        self._make_field_part(field_name, meta, writeable)

    def _make_out(self, field_name, field_data, typ):
        # type: (str, FieldData, str) -> None
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

    def _make_ext_capture(self, field_name, field_data):
        # type: (str, FieldData) -> None
        group = self._make_group("outputs")
        meta = ChoiceMeta("Capture %s in PCAP?" % field_name,
                          field_data.labels, tags=[group, Widget.COMBO.tag()])
        self._make_field_part(field_name + ".CAPTURE", meta, writeable=True)

    def _make_mux(self, field_name, field_data, port_type):
        # type: (str, FieldData, Port) -> None
        group = self._make_group("inputs")
        labels = [x for x in field_data.labels if x in ("ZERO", "ONE")] + \
            sorted(x for x in field_data.labels if x not in ("ZERO", "ONE"))
        meta = ChoiceMeta(field_data.description, labels, tags=[
            group, port_type.sink_port_tag("ZERO"),
            Widget.COMBO.tag()])
        self._make_field_part(field_name, meta, writeable=True)
        self.mux_metas[field_name] = meta

    def _make_mux_delay(self, field_name):
        # type: (str) -> None
        group = self._make_group("inputs")
        meta = NumberMeta(
            "uint8", "How many FPGA ticks to delay input",
            tags=[group, Widget.TEXTINPUT.tag()])
        self._make_field_part(field_name + ".DELAY", meta, writeable=True)

    def _make_table(self, field_name, field_data):
        # type: (str, FieldData) -> None
        group = self._make_group("parameters")
        tags = [Widget.TABLE.tag(), group, config_tag()]
        meta = TableMeta(field_data.description, tags, writeable=True)
        part = PandATablePart(
            self.client, meta, self.block_name, field_name)
        self.add_part(part)
        self.field_parts[field_name] = part

