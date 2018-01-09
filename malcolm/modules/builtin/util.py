from annotypes import Anno

from malcolm.core import VMeta, Widget, group_tag, config_tag, Port, Context, \
    Hook, APart, AContext


with Anno("Name of the created attribute"):
    Name = str
with Anno("Description of the created attribute"):
    Description = str
with Anno("Is the attribute writeable?"):
    Writeable = bool
with Anno("If given, use this widget instead of the default"):
    AWidget = Widget
with Anno("If given, which GUI group should we attach to"):
    Group = str
with Anno("If writeable, should this field be loaded/saved?"):
    Config = True
with Anno("If given, mark this as an inport of the given type"):
    InPort = Port



class InitHook(Hook):
    """Called when this controller is told to start by the process"""
    def __init__(self, part, context):
        # type: (APart, AContext) -> None
        Hook.__init__(self, part, context)


class ResetHook(Hook):
    """Called at reset() to reset all parts to a known good state"""
    def __init__(self, context):
        # type: (AContext) -> None
        super(ResetHook, self).__init__(**locals())


class HaltHook(Hook):
    """Called when this controller is told to halt"""
    def __init__(self, context):
        # type: (AContext) -> None
        super(HaltHook, self).__init__(**locals())


class DisableHook(Hook):
    """Called at disable() to stop all parts updating their attributes"""
    def __init__(self, context):
        # type: (AContext) -> None
        super(DisableHook, self).__init__(**locals())


class LayoutHook(Hook):
    """Called when layout table set and at init to update child layout"""
    def __init__(self, context, ports, layout):
        # type: (AContext, APortMap, ALayoutTable) -> None
        super(LayoutHook, self).__init__(**locals())



def set_tags(meta,  # type: VMeta
             writeable=False,  # type: Writeable
             config=True,  # type: Config
             group=None,  # type: Group
             widget=None,  # type: AWidget
             inport=None,  # type: InPort
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
