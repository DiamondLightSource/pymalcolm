from PyQt4.Qt import QAbstractItemModel, QModelIndex, Qt
from PyQt4.QtCore import pyqtSignal

from malcolm.core import Subscribe, Delta
from malcolm.gui.blockitem import BlockItem


class GuiModel(QAbstractItemModel):

    response_received = pyqtSignal(object)

    def __init__(self, process, block):
        QAbstractItemModel.__init__(self)
        self.controller = process.get_controller(block.mri)
        self.block = block
        self.id_ = 1
        self.root_item = BlockItem((self.block.mri,), block)
        # map id -> item
        self.item_lookup = {}
        # TODO: unsubscribe when done
        self.response_received.connect(self.handle_response)
        self.send_request(Subscribe(path=[self.block.mri], delta=True)).wait()

    def send_request(self, request, item=None):
        request.set_id(self.id_)
        request.set_callback(self.response_received.emit)
        self.item_lookup[self.id_] = item
        self.id_ += 1
        return self.controller.handle_request(request)

    def get_index(self, item, column):
        return self.createIndex(item.parent_row(), column, item)

    def delete_child_endpoints(self, endpoint):
        """Delete all children of item"""
        endpoints = [e for e in BlockItem.items if e!= endpoint and
                     e[:len(endpoint)] == endpoint]
        # sort by reversed length so we get children first
        endpoints.sort(key=len, reverse=True)
        for e in endpoints:
            item = BlockItem.items[e]
            parent_index = self.get_index(item.parent_item, 0)
            row = item.parent_row()
            self.beginRemoveRows(parent_index, row, row)
            item.parent_item.remove_child(item)
            self.endRemoveRows()

    def handle_response(self, response):
        if isinstance(response, Delta):
            self.handle_changes(response.changes)
        else:
            item = self.item_lookup[response.id]
            item.handle_response(response)
            index = self.get_index(item, 2)
            self.dataChanged.emit(index, index)

    def handle_changes(self, changes):
        # create and update children where necessary
        for change in changes:
            path = [self.block.mri] + change[0]
            # See if we can find an item to update
            item, path = self.find_item(path)
            # this path is the biggest thing that has to change, so delete
            # all child endpoints of this
            self.delete_child_endpoints(item.endpoint)
            # now we can update the item, creating all it's children
            self.create_children(item)

    def create_children(self, item):
        index = self.get_index(item, 0)
        nchildren = item.ref_children()
        if nchildren:
            # Added rows
            self.beginInsertRows(index, 0, nchildren - 1)
            item.create_children()
            self.endInsertRows()
        endindex = self.get_index(item, 2)
        self.dataChanged.emit(index, endindex)

    def find_item(self, endpoint):
        """Find the smallest item up from endpoint"""
        endpoint = tuple(endpoint)
        path = []
        # Keep popping the last item off the endpoint path until we get to the
        # smallest structure that we have as an item
        while endpoint:
            if endpoint in BlockItem.items:
                return BlockItem.items[endpoint], path
            path.insert(0, endpoint[-1])
            endpoint = endpoint[:-1]

    # Needed to make this a concrete model
    def index(self, row, column, parent=QModelIndex()):
        # If index out of bounds then return
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        # If valid parent item use that
        if parent.isValid():
            parent_item = parent.internalPointer()
        else:
            # otherwise we're being asked for our root item
            parent_item = self.root_item
        child_item = parent_item.children[row]
        # Now make an index
        index = self.createIndex(row, column, child_item)
        return index

    def parent(self, index):
        # Check valid index
        if not index.isValid():
            return QModelIndex()
        child_item = index.internalPointer()
        parent_item = child_item.parent_item
        # Check child's parent exists
        if parent_item is self.root_item or parent_item is None:
            return QModelIndex()
        # Return an index for us
        index = self.createIndex(parent_item.parent_row(), 0, parent_item)
        return index

    def rowCount(self, parent=QModelIndex()):
        if parent.column() > 0:
            return 0
        if parent.isValid():
            parent_item = parent.internalPointer()
        else:
            parent_item = self.root_item
        rows = len(parent_item.children)
        return rows

    def columnCount(self, parent=QModelIndex()):
        return 3

    def flags(self, index):
        flags = QAbstractItemModel.flags(self, index)
        if index.isValid() and index.column() == 1:
            item = index.internalPointer()
            if item.get_writeable():
                flags |= Qt.ItemIsEditable
        return flags

    def data(self, index, role):
        if not index.isValid():
            return None

        # Get the item
        item = index.internalPointer()
        if role in (Qt.DisplayRole, Qt.DecorationRole, Qt.EditRole):
            if index.column() == 0:
                return item.get_label()
            elif index.column() == 1:
                return str(item.get_value())
            elif index.column() == 2:
                return item.get_icon()

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole and index.isValid() and index.column() == 1:
            item = index.internalPointer()
            if item.get_writeable():
                if hasattr(value, "toString"):
                    value = value.toString()
                request = item.set_value(value)
                if request:
                    self.send_request(request, item)
                self.dataChanged.emit(index, index)
                if item.children:
                    start = self.get_index(item.children[0], 0)
                    end = self.get_index(item.children[-1], 2)
                    self.dataChanged.emit(start, end)
                return True
        return False

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                label = ["name", "value", ""][section]
                return label
