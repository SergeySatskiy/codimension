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

"""Pixmap widget"""

import os.path
from utils.pixmapcache import getIcon
from .qt import (QPalette, QSizePolicy, QScrollArea, QImage, QPixmap, QAction,
                 QLabel, QToolBar, QWidget, QHBoxLayout, QApplication, QMenu,
                 QCursor, QShortcut, Qt, QSize, pyqtSignal)
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase
from .outsidechanges import OutsideChangeWidget


FORMAT_STRINGS = {
    QImage.Format_Invalid: "invalid",
    QImage.Format_Mono: "1-bit per pixel",
    QImage.Format_MonoLSB: "1-bit per pixel",
    QImage.Format_Indexed8: "8-bit indexes",
    QImage.Format_RGB32: "32-bit RG",
    QImage.Format_ARGB32: "32-bit ARGB",
    QImage.Format_ARGB32_Premultiplied: "32-bit ARGB",
    QImage.Format_RGB16: "16-bit RGB",
    QImage.Format_ARGB8565_Premultiplied: "24-bit ARGB",
    QImage.Format_RGB666: "24-bit RGB",
    QImage.Format_ARGB6666_Premultiplied: "24-bit ARGB",
    QImage.Format_RGB555: "16-bit RGB",
    QImage.Format_ARGB8555_Premultiplied: "24-bit ARGB",
    QImage.Format_RGB888: "24-bit RGB",
    QImage.Format_RGB444: "16-bit RGB",
    QImage.Format_ARGB4444_Premultiplied: "16-bit ARGB"}


class PixmapWidget(QScrollArea):

    """The pixmap widget"""

    sigEscapePressed = pyqtSignal()

    def __init__(self, parent=None):
        QScrollArea.__init__(self, parent)

        self.pixmapLabel = QLabel()
        self.pixmapLabel.setBackgroundRole(QPalette.Base)
        self.pixmapLabel.setSizePolicy(QSizePolicy.Ignored,
                                       QSizePolicy.Ignored)
        self.pixmapLabel.setScaledContents(True)

        self.zoom = 1.0
        self.info = ""
        self.formatInfo = ""
        self.fileSize = 0

        self.setBackgroundRole(QPalette.Dark)
        self.setWidget(self.pixmapLabel)
        self.setAlignment(Qt.AlignCenter)

    def loadFromFile(self, fileName):
        """Loads a pixmap from a file"""
        image = QImage(fileName)
        if image.isNull():
            raise Exception("Unsupported pixmap format (" + fileName + ")")

        self.pixmapLabel.setPixmap(QPixmap.fromImage(image))
        self.pixmapLabel.adjustSize()

        self.fileSize = os.path.getsize(fileName)
        if self.fileSize < 1024:
            fileSizeString = str(self.fileSize) + "bytes"
        else:
            kiloBytes = self.fileSize / 1024
            if (self.fileSize % 1024) >= 512:
                kiloBytes += 1
            fileSizeString = str(kiloBytes) + "kb"
        self.info = str(image.width()) + "px/" + \
            str(image.height()) + "px/" + fileSizeString
        try:
            self.formatInfo = FORMAT_STRINGS[image.format()]
        except:
            self.formatInfo = "Unknown"
        return

    def setPixmap(self, pixmap):
        """Shows the provided pixmap"""
        pix = QPixmap.fromImage(pixmap)
        self.pixmapLabel.setPixmap(pix)
        self.pixmapLabel.adjustSize()

        self.info = str(pix.width()) + "px/" + str(pix.height()) + "px"
        self.formatInfo = str(pix.depth()) + " bpp"

    def keyPressEvent(self, event):
        """Handles the key press events"""
        if event.key() == Qt.Key_Escape:
            self.sigEscapePressed.emit()
            event.accept()
        else:
            QScrollArea.keyPressEvent(self, event)

    def resetZoom(self):
        """Resets the zoom"""
        self.zoom = 1.0
        self.pixmapLabel.adjustSize()

    def doZoom(self, factor):
        """Performs zooming"""
        self.zoom *= factor
        self.pixmapLabel.resize(self.zoom * self.pixmapLabel.pixmap().size())

        self.__adjustScrollBar(self.horizontalScrollBar(), factor)
        self.__adjustScrollBar(self.verticalScrollBar(), factor)

    def __adjustScrollBar(self, scrollBar, factor):
        """Adjusts a scrollbar by a certain factor"""
        scrollBar.setValue(int(factor * scrollBar.value() +
                               ((factor - 1) * scrollBar.pageStep() / 2)))

    def setReadOnly(self, newValue):
        """Make it similar to a text editor"""
        pass


class PixmapTabWidget(QWidget, MainWindowTabWidgetBase):

    """Pixmap viewer tab widget"""

    sigEscapePressed = pyqtSignal()
    reloadRequst = pyqtSignal()
    reloadAllNonModifiedRequest = pyqtSignal()

    def __init__(self, parent):
        MainWindowTabWidgetBase.__init__(self)
        QWidget.__init__(self, parent)

        self.__editorsManager = parent
        self.__viewer = PixmapWidget()
        self.__fileName = ""
        self.__shortName = ""

        self.__viewer.sigEscapePressed.connect(self.__onEsc)
        self.__viewer.setContextMenuPolicy(Qt.CustomContextMenu)
        self.__viewer.customContextMenuRequested.connect(self.__onContextMenu)

        self.__createLayout()

        self.__diskModTime = None
        self.__diskSize = None
        self.__reloadDlgShown = False

        self.__vcsStatus = None

    def __createLayout(self):
        """Creates the toolbar and layout"""
        # Buttons
        printButton = QAction(getIcon('printer.png'), 'Print', self)
        # printButton.setShortcut('Ctrl+')
        printButton.triggered.connect(self.__onPrint)
        printButton.setVisible(False)

        printPreviewButton = QAction(getIcon('printpreview.png'),
                                     'Print preview', self)
        # printPreviewButton.setShortcut('Ctrl+')
        printPreviewButton.triggered.connect(self.__onPrintPreview)
        printPreviewButton.setVisible(False)

        fixedSpacer = QWidget()
        fixedSpacer.setFixedHeight(16)

        zoomInButton = QAction(getIcon('zoomin.png'), 'Zoom in (Ctrl+=)', self)
        zoomInButton.setShortcut('Ctrl+=')
        zoomInButton.triggered.connect(self.onZoomIn)
        self.__zoomInSynonim = QShortcut("Ctrl++", self)
        self.__zoomInSynonim.activated.connect(self.onZoomIn)

        zoomOutButton = QAction(getIcon('zoomout.png'),
                                'Zoom out (Ctrl+-)', self)
        zoomOutButton.setShortcut('Ctrl+-')
        zoomOutButton.triggered.connect(self.onZoomOut)

        zoomResetButton = QAction(getIcon('zoomreset.png'),
                                  'Zoom reset (Ctrl+0)', self)
        zoomResetButton.setShortcut('Ctrl+0')
        zoomResetButton.triggered.connect(self.onZoomReset)

        # Toolbar
        toolbar = QToolBar(self)
        toolbar.setOrientation(Qt.Vertical)
        toolbar.setMovable(False)
        toolbar.setAllowedAreas(Qt.RightToolBarArea)
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setFixedWidth(28)
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.addAction(printPreviewButton)
        toolbar.addAction(printButton)
        toolbar.addWidget(fixedSpacer)
        toolbar.addAction(zoomInButton)
        toolbar.addAction(zoomOutButton)
        toolbar.addAction(zoomResetButton)

        hLayout = QHBoxLayout()
        hLayout.setContentsMargins(0, 0, 0, 0)
        hLayout.setSpacing(0)
        hLayout.addWidget(self.__viewer)
        hLayout.addWidget(toolbar)

        self.__outsideChangesBar = OutsideChangeWidget(self.__viewer)
        self.__outsideChangesBar.sigReloadRequest.connect(self.__onReload)
        self.__outsideChangesBar.reloadAllNonModifiedRequest.connect(
            self.reloadAllNonModified)
        self.__outsideChangesBar.hide()

        self.setLayout(hLayout)

    def setFocus(self):
        """Overridden setFocus"""
        if self.__outsideChangesBar.isHidden():
            self.__viewer.setFocus()
        else:
            self.__outsideChangesBar.setFocus()

    def loadFromFile(self, path):
        """Loads the content from the given file"""
        self.__viewer.loadFromFile(path)
        self.setFileName(os.path.abspath(path))

        # Memorize the modification date
        path = os.path.realpath(path)
        self.__diskModTime = os.path.getmtime(path)
        self.__diskSize = os.path.getsize(path)

    def setPixmap(self, pixmap):
        """Loads the provided pixmap"""
        self.__viewer.setPixmap(pixmap)
        self.__diskModTime = None
        self.__diskSize = None

    def __onPrint(self):
        """Triggered on the 'print' button"""
        pass

    def __onPrintPreview(self):
        """Triggered on the 'print preview' button"""
        pass

    def onZoomIn(self):
        """Triggered on the 'zoom in' button"""
        self.__viewer.doZoom(1.25)
        QApplication.processEvents()
        self.resizeBars()

    def onZoomOut(self):
        """Triggered on the 'zoom out' button"""
        self.__viewer.doZoom(0.8)
        QApplication.processEvents()
        self.resizeBars()

    def wheelEvent(self, event):
        """Mouse wheel event"""
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            angleDelta = event.angleDelta()
            if not angleDelta.isNull():
                if angleDelta.y() > 0:
                    self.onZoomIn()
                else:
                    self.onZoomOut()
            event.accept()
        else:
            QWidget.wheelEvent(self, event)

    def __onContextMenu(self, pos):
        """Triggered when a context menu is requested"""
        del pos     # unused argument
        pluginMenus = self.__editorsManager.getPluginMenus()
        if pluginMenus:
            contextMenu = QMenu()
            for pluginPath, pluginMenu in pluginMenus.iteritems():
                del pluginPath  # unused variable
                contextMenu.addMenu(pluginMenu)
            contextMenu.exec_(QCursor.pos())
            del contextMenu

    def onZoomReset(self):
        """Triggered on the 'zoom reset' button"""
        self.__viewer.resetZoom()
        QApplication.processEvents()
        self.resizeBars()

    def __onEsc(self):
        """Triggered when Esc is pressed"""
        self.sigEscapePressed.emit()

    def resizeEvent(self, event):
        """Resizes the outside changes dialogue if necessary"""
        QWidget.resizeEvent(self, event)
        self.resizeBars()

    def resizeBars(self):
        """Resize the bars if they are shown"""
        if not self.__outsideChangesBar.isHidden():
            self.__outsideChangesBar.resize()

    def __onReload(self):
        """Triggered when a request to reload the file is received"""
        self.reloadRequst.emit()

    def reloadAllNonModified(self):
        """Triggered when a request to reload all the
           non-modified files is received
        """
        self.reloadAllNonModifiedRequest.emit()

    def showOutsideChangesBar(self, allEnabled):
        """Shows the bar for the viewer for the user to choose the action"""
        self.setReloadDialogShown(True)
        self.__outsideChangesBar.showChoice(self.isModified(), allEnabled)

    def reload(self):
        """Called (from the editors manager) to reload the file"""
        # Re-read the file with updating the file timestamp
        self.loadFromFile(self.__fileName)

        # Hide the bar is necessery
        if not self.__outsideChangesBar.isHidden():
            self.__outsideChangesBar.hide()

        # Set the shown flag
        self.setReloadDialogShown(False)

    # Mandatory interface part is below

    def isModified(self):
        """Tells if the file is modified"""
        return False

    def getRWMode(self):
        """Tells if the file is read only"""
        return "RO"

    def getType(self):
        """Tells the widget type"""
        return MainWindowTabWidgetBase.PictureViewer

    def getLanguage(self):
        """Tells the content language"""
        return self.__viewer.formatInfo

    def getFileName(self):
        """Tells what file name of the widget content"""
        return self.__fileName

    def setFileName(self, name):
        """Sets the file name"""
        self.__fileName = name
        self.__shortName = os.path.basename(name)

    def getEncoding(self):
        """Tells the content encoding"""
        return self.__viewer.info

    def setEncoding(self, newEncoding):
        """Sets the encoding - not applicable for picture viewer"""
        pass

    def getShortName(self):
        """Tells the display name"""
        return self.__shortName

    def setShortName(self, name):
        """Sets the display name"""
        self.__shortName = name

    def isDiskFileModified(self):
        """Return True if the loaded file is modified"""
        if not os.path.isabs(self.__fileName):
            return False
        if not os.path.exists(self.__fileName):
            return True
        path = os.path.realpath(self.__fileName)
        return self.__diskModTime != os.path.getmtime(path) or \
            self.__diskSize != os.path.getsize(path)

    def doesFileExist(self):
        """Returns True if the loaded file still exists"""
        return os.path.exists(self.__fileName)

    def setReloadDialogShown(self, value=True):
        """Sets the new value of the flag which tells if the reloading
           dialogue has already been displayed
        """
        self.__reloadDlgShown = value

    def getReloadDialogShown(self):
        """Tells if the reload dialog has already been shown"""
        return self.__reloadDlgShown and \
            not self.__outsideChangesBar.isVisible()

    def updateModificationTime(self, fileName):
        """Updates the modification time"""
        path = os.path.realpath(fileName)
        self.__diskModTime = os.path.getmtime(path)
        self.__diskSize = os.path.getsize(path)

    def getVCSStatus(self):
        """Provides the VCS status"""
        return self.__vcsStatus

    def setVCSStatus(self, newStatus):
        """Sets the new VCS status"""
        self.__vcsStatus = newStatus
