# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Disassembler widget"""

from ui.mainwindowtabwidgetbase import MainWindowTabWidgetBase
from ui.qt import (Qt, QSize, QEvent, pyqtSignal, QWidget, QToolBar,
                   QHBoxLayout, QAction, QLabel, QFrame, QPalette, QVBoxLayout,
                   QPlainTextEdit, QSizePolicy, QApplication)
from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from utils.misc import extendInstance
from utils.colorfont import getZoomedMonoFont
from utils.settings import Settings


class DisasmWidget(QPlainTextEdit):

    """Wraps QPlainTextEdit to have a keyboard handler"""

    def __init__(self, parent):
        QPlainTextEdit.__init__(self, parent)
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Event filter to catch shortcuts on UBUNTU"""
        if event.type() == QEvent.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            if modifiers == Qt.ControlModifier:
                if key == Qt.Key_Minus:
                    Settings().onTextZoomOut()
                    return True
                if key == Qt.Key_Equal:
                    Settings().onTextZoomIn()
                    return True
                if key == Qt.Key_0:
                    Settings().onTextZoomReset()
                    return True

        return QPlainTextEdit.eventFilter(self, obj, event)

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

    def onTextZoomChanged(self):
        """Triggered when a text zoom is changed"""
        self.setFont(getZoomedMonoFont())


class DisassemblerResultsWidget(QWidget):

    """Disassembling results widget"""

    sigEscapePressed = pyqtSignal()

    def __init__(self, scriptName, name, code, reportTime, parent=None):
        QWidget.__init__(self, parent)

        extendInstance(self, MainWindowTabWidgetBase)
        MainWindowTabWidgetBase.__init__(self)

        self.__createLayout(scriptName, name, code, reportTime)
        self.onTextZoomChanged()

    def __createLayout(self, scriptName, name, code, reportTime):
        """Creates the toolbar and layout"""

        # Buttons
        self.__printButton = QAction(getIcon('printer.png'), 'Print', self)
        self.__printButton.triggered.connect(self.__onPrint)
        self.__printButton.setEnabled(False)
        self.__printButton.setVisible(False)

        self.__printPreviewButton = QAction(getIcon('printpreview.png'),
                                            'Print preview', self)
        self.__printPreviewButton.triggered.connect(self.__onPrintPreview)
        self.__printPreviewButton.setEnabled(False)
        self.__printPreviewButton.setVisible(False)

        # Zoom buttons
        self.__zoomInButton = QAction(getIcon('zoomin.png'),
                                      'Zoom in (Ctrl+=)', self)
        self.__zoomInButton.triggered.connect(Settings().onTextZoomIn)

        self.__zoomOutButton = QAction(getIcon('zoomout.png'),
                                       'Zoom out (Ctrl+-)', self)
        self.__zoomOutButton.triggered.connect(Settings().onTextZoomOut)

        self.__zoomResetButton = QAction(getIcon('zoomreset.png'),
                                         'Zoom reset (Ctrl+0)', self)
        self.__zoomResetButton.triggered.connect(Settings().onTextZoomReset)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Toolbar
        toolbar = QToolBar(self)
        toolbar.setOrientation(Qt.Vertical)
        toolbar.setMovable(False)
        toolbar.setAllowedAreas(Qt.RightToolBarArea)
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setFixedWidth(28)
        toolbar.setContentsMargins(0, 0, 0, 0)

        toolbar.addAction(self.__printPreviewButton)
        toolbar.addAction(self.__printButton)
        toolbar.addWidget(spacer)
        toolbar.addAction(self.__zoomInButton)
        toolbar.addAction(self.__zoomOutButton)
        toolbar.addAction(self.__zoomResetButton)

        summary = QLabel("<b>Script:</b> " + scriptName + "<br/>"
                         "<b>Name:</b> " + name + "<br/>"
                         "<b>Disassembled at:</b> " + reportTime)
        summary.setFrameStyle(QFrame.StyledPanel)
        summary.setAutoFillBackground(True)
        summaryPalette = summary.palette()
        summaryBackground = summaryPalette.color(QPalette.Background)
        summaryBackground.setRgb(min(summaryBackground.red() + 30, 255),
                                 min(summaryBackground.green() + 30, 255),
                                 min(summaryBackground.blue() + 30, 255))
        summaryPalette.setColor(QPalette.Background, summaryBackground)
        summary.setPalette(summaryPalette)

        self.__text = DisasmWidget(self)
        self.__text.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.__text.setReadOnly(True)
        self.__text.setPlainText(code)

        vLayout = QVBoxLayout()
        vLayout.addWidget(summary)
        vLayout.addWidget(self.__text)

        hLayout = QHBoxLayout()
        hLayout.setContentsMargins(0, 0, 0, 0)
        hLayout.setSpacing(0)
        hLayout.addLayout(vLayout)
        hLayout.addWidget(toolbar)

        self.setLayout(hLayout)

    def setFocus(self):
        """Overriden setFocus"""
        self.__text.setFocus()

    def __onPrint(self):
        """Triggered on the 'print' button"""
        pass

    def __onPrintPreview(self):
        """Triggered on the 'print preview' button"""
        pass

    def keyPressEvent(self, event):
        """Handles the key press events"""
        if event.key() == Qt.Key_Escape:
            self.sigEscapePressed.emit()
            event.accept()
        else:
            QWidget.keyPressEvent(self, event)

    def onTextZoomChanged(self):
        """Triggered when a text zoom is changed"""
        self.__text.onTextZoomChanged()

    # Mandatory interface part is below

    def isModified(self):
        """Tells if the file is modified"""
        return False

    def getRWMode(self):
        """Tells if the file is read only"""
        return "RO"

    def getType(self):
        """Tells the widget type"""
        return MainWindowTabWidgetBase.DisassemblerViewer

    def getLanguage(self):
        """Tells the content language"""
        return "Disassembler"

    def setFileName(self, name):
        """Sets the file name - not applicable"""
        raise Exception("Setting a file name for disassembler "
                        "results is not applicable")

    def setEncoding(self, newEncoding):
        """Sets the new encoding - not applicable for
           the disassembler results viewer
        """
        return

    def getShortName(self):
        """Tells the display name"""
        return "Disassembling results"

    def setShortName(self, name):
        """Sets the display name - not applicable"""
        raise Exception("Setting a file name for disassembler "
                        "results is not applicable")
