import os
from typing import Any, Dict, Optional, Union, cast

from annotypes import Anno

from malcolm.core import (
    Alarm,
    AMri,
    BooleanMeta,
    ChoiceMeta,
    NumberMeta,
    Port,
    StringMeta,
    TableMeta,
    TimeStamp,
    VMeta,
    Widget,
    badge_value_tag,
    config_tag,
    group_tag,
    linked_value_tag,
    snake_to_camel,
    without_linked_value_tags,
)
from malcolm.modules import builtin

from ..pandablocksclient import BlockData, FieldData
from ..parts.pandaactionpart import PandAActionPart
from ..parts.pandafieldpart import PandAFieldPart
from ..parts.pandaiconpart import PandAIconPart
from ..parts.pandalabelpart import PandALabelPart
from ..parts.pandaluticonpart import PandALutIconPart
from ..parts.pandapulseiconpart import PandAPulseIconPart
from ..parts.pandasrgateiconpart import PandASRGateIconPart
from ..parts.pandatablepart import PandATablePart
from ..util import SVG_DIR, ABlockName, AClient, ADocUrlBase

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
        raise ValueError(f"Unknown subtype {subtyp!r}")
    meta.set_writeable(writeable)
    tags.append(meta.default_widget().tag())
    meta.set_tags(tags)
    return meta


class PandABlockController(builtin.controllers.BasicController):
    def __init__(
        self,
        client: AClient,
        mri_prefix: AMri,
        block_name: ABlockName,
        block_data: ABlockData,
        doc_url_base: ADocUrlBase,
    ) -> None:
        super().__init__(mri=f"{mri_prefix}:{block_name}")
        # Store
        self.client = client
        self.mri_prefix = mri_prefix
        self.block_name = block_name
        self.block_data = block_data
        self.doc_url_base = doc_url_base
        # {field_name: part}
        self.field_parts: Dict[str, Optional[ChangeHandler]] = {}
        # {field_name: attr.meta}
        self.mux_metas: Dict[str, VMeta] = {}
        # Make an icon, label and help for the Block
        self.icon_part: PandAIconPart = self._make_common_parts()
        # Create parts for each field
        for field_name, field_data in block_data.fields.items():
            self._make_parts_for(field_name, field_data)

    def handle_changes(self, changes: Dict[str, Any], ts: TimeStamp) -> None:
        with self.changes_squashed:
            icon_needs_update = False
            if isinstance(changes, Dict):
                for k, v in changes.items():
                    # Health changes are for us
                    if k.upper() == "HEALTH":
                        if v.upper() == "OK":
                            alarm = Alarm.ok
                        else:
                            alarm = Alarm.major(v)
                        self.update_health(
                            self, builtin.infos.HealthInfo(cast(Alarm, alarm), ts)
                        )
                        continue
                    # Work out if there is a part we need to notify
                    try:
                        part = self.field_parts[k]
                    except KeyError:
                        self.log.exception(f"Can't handle field {self.block_name}.{k}")
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
                d = {}
                for key in self.icon_part.update_fields:
                    if key in self.field_parts:
                        field_part = self.field_parts[key]
                        if field_part:
                            d[key] = field_part.attr.value
                icon = builtin.util.SVGIcon(self.icon_part.svg_text)
                self.icon_part.update_icon(icon, d)
                self.icon_part.attr.set_value(str(icon), ts=ts)

    def _handle_mux_update(self, mux_meta, v):
        # Mux changed its value, update its link to a different
        # Attribute
        tags = without_linked_value_tags(mux_meta.tags)
        split = v.split(".")
        if len(split) == 2:
            block_name, field_name = split
            attr_name = snake_to_camel(field_name.replace(".", "_"))
            block_mri = f"{self.mri_prefix}:{block_name}"
            tags.append(linked_value_tag(block_mri, attr_name))
        mux_meta.set_tags(tags)

    def _make_common_parts(self) -> PandAIconPart:
        block_type = self.block_name.rstrip("0123456789")
        block_number = self.block_name[len(block_type) :]
        svg_path = os.path.join(SVG_DIR, block_type + ".svg")
        if block_type == "LUT":
            icon_cls = PandALutIconPart
        elif block_type in ("PULSE", "PCAP"):
            icon_cls = PandAPulseIconPart
        elif block_type == "SRGATE":
            icon_cls = PandASRGateIconPart
        else:
            icon_cls = PandAIconPart
        icon_part = icon_cls(self.client, self.block_name, svg_path)
        self.add_part(icon_part)
        label = self.block_data.description
        metadata_field = f"LABEL_{self.block_name}"
        if block_number:
            # If we have multiple blocks, make the labels unique
            label += f" {block_number}"
        else:
            # If we only have one block, the metadata field still has numbers
            metadata_field += "1"
        label_part = PandALabelPart(self.client, metadata_field, value=label)
        self.add_part(label_part)
        self.field_parts["LABEL"] = label_part
        self.add_part(
            builtin.parts.HelpPart(
                f"{self.doc_url_base}/build/{block_type.lower()}_doc.html"
            )
        )
        return icon_part

    def _make_parts_for(self, field_name, field_data):
        """Create the relevant parts for this field

        Args:
            field_name (str): Short field name, e.g. VAL
            field_data (FieldData): Field data object
        """
        if field_name.upper() == "HEALTH":
            # Ignore health, as we already have a health field
            return

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
                self.field_parts[f"{field_name}.{suffix}"] = None
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
            raise ValueError(f"Unknown type {typ!r} subtype {subtyp!r}")

    def _make_group(self, attr_name: str) -> str:
        if attr_name not in self.parts:
            self.add_part(
                builtin.parts.GroupPart(attr_name, f"All {attr_name} attributes")
            )
        group = group_tag(attr_name)
        return group

    def _make_field_part(
        self, field_name, meta, writeable, initial_value=None, iteration=1
    ):
        if writeable:
            meta.set_tags(list(meta.tags) + [config_tag(iteration)])
            meta.set_writeable(True)
        part = PandAFieldPart(
            self.client, meta, self.block_name, field_name, initial_value
        )
        self.add_part(part)
        self.field_parts[field_name] = part

    def _make_time(
        self, field_name: str, field_data: FieldData, writeable: bool
    ) -> None:
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
        meta = ChoiceMeta(
            description + " time units",
            ["s", "ms", "us"],
            tags=[group, Widget.COMBO.tag()],
        )
        self._make_field_part(field_name + ".UNITS", meta, writeable=True)

    def _make_action(self, field_name: str, field_data: FieldData) -> None:
        group = self._make_group("parameters")
        self.add_part(
            PandAActionPart(
                self.client,
                self.block_name,
                field_name,
                field_data.description,
                [group],
            )
        )

    def _make_param(
        self, field_name: str, field_data: FieldData, writeable: bool
    ) -> None:
        if writeable:
            group = self._make_group("parameters")
        else:
            group = self._make_group("readbacks")
        meta = make_meta(
            field_data.field_subtype,
            field_data.description,
            [group],
            writeable,
            field_data.labels,
        )
        self._make_field_part(field_name, meta, writeable)

    def _make_out(self, field_name: str, field_data: FieldData, typ: str) -> None:
        group = self._make_group("outputs")
        if typ == "bit":
            port_type = Port.BOOL
        else:
            port_type = Port.INT32
        flow_tag = port_type.source_port_tag(f"{self.block_name}.{field_name}")
        meta = make_meta(
            typ, field_data.description, tags=[group, flow_tag], writeable=False
        )
        self._make_field_part(field_name, meta, writeable=False)

    def _make_ext_capture(self, field_name: str, field_data: FieldData) -> None:
        group = self._make_group("outputs")
        meta = ChoiceMeta(
            f"Capture {field_name} in PCAP?",
            field_data.labels,
            tags=[group, Widget.COMBO.tag()],
        )
        self._make_field_part(field_name + ".CAPTURE", meta, writeable=True)

    def _make_mux(
        self, field_name: str, field_data: FieldData, port_type: Port
    ) -> None:
        group = self._make_group("inputs")
        labels = [x for x in field_data.labels if x in ("ZERO", "ONE")] + sorted(
            x for x in field_data.labels if x not in ("ZERO", "ONE")
        )
        tags = [group, port_type.sink_port_tag("ZERO"), Widget.COMBO.tag()]
        if port_type == Port.BOOL:
            # Bits have a delay, use it as a badge
            delay_name = snake_to_camel(field_name) + "Delay"
            tags.append(badge_value_tag(self.mri, delay_name))
        meta = ChoiceMeta(field_data.description, labels, tags=tags)
        self._make_field_part(field_name, meta, writeable=True)
        self.mux_metas[field_name] = meta

    def _make_mux_delay(self, field_name: str) -> None:
        group = self._make_group("inputs")
        meta = NumberMeta(
            "uint8",
            "How many FPGA ticks to delay input",
            tags=[group, Widget.TEXTINPUT.tag()],
        )
        self._make_field_part(field_name + ".DELAY", meta, writeable=True)

    def _make_table(self, field_name: str, field_data: FieldData) -> None:
        group = self._make_group("parameters")
        tags = [Widget.TABLE.tag(), group, config_tag()]
        meta = TableMeta(field_data.description, tags, writeable=True)
        part = PandATablePart(self.client, meta, self.block_name, field_name)
        self.add_part(part)
        self.field_parts[field_name] = part
