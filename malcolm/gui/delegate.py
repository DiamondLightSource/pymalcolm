from PyQt4.Qt import QStyledItemDelegate, QStyle, QStyleOptionButton, \
    QApplication, QEvent, QPushButton, QComboBox, QLineEdit, QVariant, Qt

from malcolm.gui.attributeitem import AttributeItem
from malcolm.gui.parameteritem import ParameterItem
from malcolm.gui.methoditem import MethodItem


class Delegate(QStyledItemDelegate):

    def createEditor(self, parent, option, index):
        if index.isValid() and index.column() == 1:
            item = index.internalPointer()
            if isinstance(item, (AttributeItem, ParameterItem)):
                if False: #item.meta["metaOf"] == "malcolm:core/Enum:1.0":
                    editor = SpecialComboBox(parent)
                    editor.delegate = self
                    editor.setEditable(True)
                    editor.addItems(item.meta["oneOf"])
                elif False: #item.meta["metaOf"] == "malcolm:core/Boolean:1.0":
                    editor = SpecialComboBox(parent)
                    editor.delegate = self
                    editor.setEditable(True)
                    editor.addItems(["False", "True"])
                else:
                    editor = QLineEdit(parent)
                return editor

    def setEditorData(self, editor, index):
        if isinstance(editor, QComboBox):
            i = editor.findText(index.data(Qt.EditRole).toString())
            if i > -1:
                editor.setCurrentIndex(i)
            else:
                editor.setEditText(index.data(Qt.EditRole).toString())
            editor.lineEdit().selectAll()
        else:
            return QStyledItemDelegate.setEditorData(self, editor, index)

    def setModelData(self, editor, model, index):
        if isinstance(editor, QComboBox):
            model.setData(index, QVariant(editor.currentText()), Qt.EditRole)
        else:
            return QStyledItemDelegate.setModelData(self, editor, model, index)

    def is_method_button(self, index):
        if index.isValid() and isinstance(index.internalPointer(), MethodItem):
            column = index.column()
            if column == 1:
                return True
        return False

    def paint(self, painter, option, index):
        # If we are looking at a method then draw a button
        # http://www.qtcentre.org/threads/26916-inserting-custom-Widget-to-listview?p=128623#post128623
        if self.is_method_button(index):
            item = index.internalPointer()
            opt = QStyleOptionButton()
            style = QApplication.style()
            # If method is running, draw sunken
            if item.get_state() == item.RUNNING:
                opt.state |= QStyle.State_Enabled
                opt.state |= QStyle.State_Sunken
            # if method is allowed, draw blue
            elif item.get_writeable():
                opt.state |= QStyle.State_Enabled
            # if we are hovering, draw highlight
            if option.state & QStyle.State_MouseOver:
                opt.state |= QStyle.State_MouseOver
            opt.rect = option.rect
            opt.text = item.get_label()
            style.drawControl(QStyle.CE_PushButton, opt, painter, QPushButton())
        else:
            if option.state & QStyle.State_Selected:
                # Don't show delegates as highlighted
                option.state = option.state ^ QStyle.State_Selected
            QStyledItemDelegate.paint(self, painter, option, index)

    def editorEvent(self, event, model, option, index):
        if self.is_method_button(index):
            # TODO: Drag seems to do the wrong thing here...
            if event.type() in [QEvent.MouseButtonPress,
                                QEvent.MouseButtonDblClick]:
                return model.setData(index, None)
        return QStyledItemDelegate.editorEvent(self, event, model, option, index)


class SpecialComboBox(QComboBox):
    # Qt outputs an activated signal if you start typing then mouse click on the
    # down arrow. By delaying the activated event until after the mouse click
    # we avoid this problem
    def closeEvent(self, i):
        self.delegate.commitData.emit(self)
        self.delegate.closeEditor.emit(self, QStyledItemDelegate.SubmitModelCache)

    def mousePressEvent(self, event):
        QComboBox.mousePressEvent(self, event)
        self.activated.connect(self.closeEvent)
