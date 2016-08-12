from PyQt4.Qt import QTreeView, QSize

from malcolm.gui.blockmodel import BlockModel
from malcolm.gui.delegate import Delegate


class BlockGui(QTreeView):

    def __init__(self, process, block):
        QTreeView.__init__(self)
        model = BlockModel(process, block)
        self.setModel(model)
        self.setColumnWidth(0, 160)
        self.setColumnWidth(1, 180)
        self.setColumnWidth(2, 25)
        self.resize(QSize(370, 800))
        self.setItemDelegateForColumn(1, Delegate())
        self.setEditTriggers(self.AllEditTriggers)
        self.show()
