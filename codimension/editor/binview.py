# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2020 Sergey Satskiy <sergey.satskiy@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from ui.qt import (QWidget, QSizePolicy,QVBoxLayout, QPlainTextEdit, QTimer,
                   Qt, QApplication, QEvent)
from ui.labels import HeaderLabel
from utils.colorfont import getZoomedMonoFont
from utils.settings import Settings
from utils.misc import splitThousands
from analysis.disasm import getFileBinary, getBufferBinary


class BinViewTextEditor(QPlainTextEdit):

    """Needs to intercept Ctrl+- Ctrl+= Ctrl+0"""

    def __init__(self, parent):
        QPlainTextEdit.__init__(self, parent)

        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setFont(getZoomedMonoFont())
        self.setReadOnly(True)

        self.installEventFilter(self)

    # Arguments: obj, event
    def eventFilter(self, _, event):
        """Event filter to catch shortcuts on UBUNTU"""
        if event.type() == QEvent.KeyPress:
            modifiers = event.modifiers()
            if modifiers == Qt.ControlModifier:
                key = event.key()
                if key == Qt.Key_Minus:
                    Settings().onTextZoomOut()
                    return True
                if key == Qt.Key_Equal:
                    Settings().onTextZoomIn()
                    return True
                if key == Qt.Key_0:
                    Settings().onTextZoomReset()
                    return True
        return False

    def wheelEvent(self, event):
        """Mouse wheel event"""
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            angleDelta = event.angleDelta()
            if not angleDelta.isNull():
                if angleDelta.y() > 0:
                    Settings().onTextZoomIn()
                else:
                    Settings().onTextZoomOut()
            event.accept()
        else:
            QPlainTextEdit.wheelEvent(self, event)


class BinView(QWidget):

    def __init__(self, navBar, parent):
        QWidget.__init__(self, parent)
        self.__navBar = navBar

        self.__textEdit = BinViewTextEditor(self)

        self.__summary = HeaderLabel(parent=self)
        self.__summary.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Maximum)
        self.__summary.setMinimumWidth(10)
        self.__summary.setVisible(False)

        vLayout = QVBoxLayout()
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(0)
        vLayout.addWidget(self.__summary)
        vLayout.addWidget(self.__textEdit)

        self.setLayout(vLayout)

        Settings().sigTextZoomChanged.connect(self.onTextZoomChanged)

    def onTextZoomChanged(self):
        """The mono font has been globally changed"""
        self.__textEdit.setFont(getZoomedMonoFont())

    def serializeScrollAndSelection(self):
        """Memorizes the selection and expanded items"""
        self.__hScroll = self.__textEdit.horizontalScrollBar().value()
        self.__vScroll = self.__textEdit.verticalScrollBar().value()

    def restoreScrollAndSelection(self):
        """Restores the selection and scroll position"""
        self.__textEdit.horizontalScrollBar().setValue(self.__hScroll)
        self.__textEdit.verticalScrollBar().setValue(self.__vScroll)

    def populateBinary(self, source, encoding, filename):
        """Populates the disassembly tree"""
        self.__navBar.clearWarnings()
        self.serializeScrollAndSelection()
        try:
            optLevel = Settings()['disasmLevel']
            if source is None:
                props, binContent = getFileBinary(
                    filename, optLevel)
            else:
                props, binContent = getBufferBinary(
                    source, encoding, filename, optLevel)

            self.__textEdit.clear()

            self.__populate(binContent, props)
            self.__setupLabel(props)

            self.__navBar.updateInfoIcon(self.__navBar.STATE_OK_UTD)

            QTimer.singleShot(0, self.restoreScrollAndSelection)
        except Exception as exc:
            self.__navBar.updateInfoIcon(self.__navBar.STATE_BROKEN_UTD)
            self.__navBar.setErrors('Binary view populating error:\n' +
                                    str(exc))

    def __setupLabel(self, props):
        """Updates the property label"""
        txt = ''
        for item in props:
            if txt:
                txt += '<br/>'
            txt += '<b>' + item[0] + ':</b> ' + item[1]
        self.__summary.setText(txt)
        self.__summary.setToolTip(txt)
        self.__summary.setVisible(True)

    def __populate(self, binContent, props):
        """Populates binary view"""
        address = 0
        currentLine = ''
        asciiLine = ''
        for char in binContent:
            if address % 16 == 0:
                currentLine = hex(address).lstrip('0x').rstrip('L').rjust(8, '0') + '  '
            currentLine += hex(char).lstrip('0x').rjust(2, '0') + ' '
            if char < 32:
                asciiLine += '.'
            else:
                charRepr = chr(char)
                if len(repr(charRepr)) > 3:
                    asciiLine += '.'
                else:
                    asciiLine += charRepr

            address += 1
            if address % 8 == 0:
                currentLine += ' '
            if address % 16 == 0:
                self.__textEdit.appendPlainText(currentLine +
                                                '|' + asciiLine + '|')
                currentLine = ''
                asciiLine = ''

        if currentLine:
            self.__textEdit.appendPlainText(currentLine.ljust(60, ' ') +
                                            '|' + asciiLine + '|')

        props.append(('Size', splitThousands(str(address)) + ' bytes'))

