from PyQt4.Qt import QStyle, QApplication


class BaseItem(object):
    IDLE = "Idle"
    RUNNING = "Run"
    ERROR = "Error"
    CHANGED = "Changed"
    icons = {
        IDLE: QStyle.SP_FileDialogInfoView,
        RUNNING: QStyle.SP_BrowserReload,
        ERROR: QStyle.SP_MessageBoxCritical,
        CHANGED: QStyle.SP_FileDialogStart,
    }
    # map endpoint -> BlockItem
    items = {}

    def __init__(self, endpoint, ref):
        # The Block or Method or Attribute or AttributeMeta ref
        self.ref = ref
        # parent BlockItem
        self.parent_item = None
        # any BlockItem children
        self.children = []
        # endpoint list for this node
        self.endpoint = tuple(endpoint)
        # add to items
        self.items[self.endpoint] = self
        # current state
        self._state = self.IDLE

    def get_icon(self):
        icon = self.icons[self.get_state()]
        return QApplication.style().standardIcon(icon)

    def get_label(self):
        return self.endpoint[-1]

    def get_value(self):
        return None

    def get_writeable(self):
        return False

    def get_state(self):
        return self._state

    def parent_row(self):
        if self.parent_item:
            assert self in self.parent_item.children, \
                "%s is not in %s" % (self, self.parent_item.children)
            return self.parent_item.children.index(self)
        return 0

    def add_child(self, item):
        item.parent_item = self
        self.children.append(item)
        self.items[item.endpoint] = item

    def remove_child(self, item):
        self.children.remove(item)
        self.items.pop(item.endpoint)

    def ref_children(self):
        return 0

    def create_children(self):
        return

    def set_value(self, value):
        raise NotImplementedError()

