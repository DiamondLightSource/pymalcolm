import os

from PyQt4.Qt import QTreeView, QSize, QIcon

from malcolm.gui.guimodel import GuiModel
from malcolm.gui.delegate import Delegate
from malcolm.gui.attributeitem import AttributeItem


class BlockGui(QTreeView):

    def __init__(self, process, block):
        QTreeView.__init__(self)
        model = GuiModel(process, block)
        self.setModel(model)
        self.setWindowTitle("%s: imalcolm" % model.block.mri)
        root = os.path.join(os.path.dirname(__file__), "..", "..")
        icon_path = os.path.join(root, "docs", "malcolm-logo.svg")
        self.setWindowIcon(QIcon(icon_path))
        self.setColumnWidth(0, 160)
        self.setColumnWidth(1, 180)
        self.setColumnWidth(2, 25)
        self.resize(QSize(370, 500))
        self.setItemDelegateForColumn(1, Delegate())
        self.setEditTriggers(self.AllEditTriggers)
        self.expanded.connect(self.write_expanded)
        self.collapsed.connect(self.write_collapsed)

    def write_expanded(self, index):
        self._write_group(index, "expanded")

    def write_collapsed(self, index):
        self._write_group(index, "collapsed")

    def dataChanged(self, topLeft, bottomRight):
        model = self.model()
        for row in range(model.rowCount()):
            str_data = str(model.index(row, 1).data().toString())
            index = model.index(row, 0)
            if str_data == "expanded":
                self.setExpanded(index, True)
            elif str_data == "collapsed":
                self.setExpanded(index, False)
        super(BlockGui, self).dataChanged(topLeft, bottomRight)

    def _write_group(self, index, value):
        item = index.internalPointer()
        if isinstance(item, AttributeItem):
            model = self.model()
            index = model.index(index.row(), 1, index.parent())
            model.setData(index, value)




