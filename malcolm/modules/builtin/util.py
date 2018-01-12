from annotypes import Anno

from malcolm.core import VMeta, Widget, group_tag, config_tag, Port


with Anno("Is the attribute writeable?"):
    AWriteable = bool
with Anno("If writeable, should this field be loaded/saved?"):
    AConfig = True
with Anno("If given, which GUI group should we attach to"):
    AGroup = str
with Anno("If given, use this widget instead of the default"):
    AWidget = Widget
with Anno("If given, mark this as an inport of the given type"):
    AInPort = Port


def set_tags(meta,  # type: VMeta
             writeable=False,  # type: AWriteable
             config=True,  # type: AConfig
             group=None,  # type: AGroup
             widget=None,  # type: AWidget
             inport=None,  # type: AInPort
             ):
    # type: (...) -> None
    tags = []
    if widget is None:
        widget = meta.default_widget()
    if widget is not Widget.NONE:
        tags.append(widget.tag())
    if config and writeable:
        # We only allow config tags on writeable functions
        tags.append(config_tag())
    if group:
        # If we have a group then add the tag
        tags.append(group_tag(group))
    if inport:
        tags.append(inport.inport_tag(disconnected_value=""))
    meta.set_tags(tags)
