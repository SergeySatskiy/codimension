# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2018  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""MD rendering widget"""


import logging
import os.path
import re
from ui.qt import (Qt, QSize, QTimer, QToolBar, QWidget, QHBoxLayout,
                   QLabel, QVBoxLayout, QSizePolicy, QFrame, QDesktopServices,
                   pyqtSignal, QPrintDialog, QDialog, QAction, QPixmap,
                   QTextDocument)
from ui.texttabwidget import TextViewer
from utils.fileutils import isMarkdownMime
from utils.pixmapcache import getPixmap, getIcon
from utils.globals import GlobalData
from utils.settings import Settings
from utils.diskvaluesrelay import getFilePosition
from utils.md import renderMarkdown


IDLE_TIMEOUT = 1500


class MDViewer(TextViewer):

    """Markdown rendered content viewer"""

    def __init__(self, parent):
        TextViewer.__init__(self, parent)

        self.__parentWidget = parent
        self.setViewportMargins(10, 10, 10, 10)
        self.setOpenExternalLinks(True)
        self.setOpenLinks(False)
        self.anchorClicked.connect(self._onAnchorClicked)

        self.__lineNoExpr = re.compile(r':\d+$')

        Settings().webResourceCache.sigResourceSaved.connect(
            self.onResourceSaved)

    def _resolveLink(self, link):
        """Resolves the link to a file and optional line number"""
        scheme = link.scheme().lower()
        if scheme in ['http', 'https']:
            QDesktopServices.openUrl(link)
            return None, None

        if scheme == '':
            fileName = link.path()
        elif scheme == 'file':
            if link.isValid():
                fileName = link.path()
            else:
                logging.error('Invalid link: ' + link.errorString())
                return None, None
        else:
            logging.error("Unsupported url scheme '" + link.scheme() +
                          "'. Supported schemes are 'http', 'https', 'file' "
                          "and an empty scheme for files")
            return None, None

        if not fileName:
            logging.error('Could not get a file name. Check the link format. '
                          'Valid examples: file:./relative/fname or '
                          'file:relative/fname or file:/absolute/fname or '
                          'file:///absolute/fname')
            return None, None

        lineNo = -1
        match = self.__lineNoExpr.search(fileName)
        if match is not None:
            linePart = match.group()
            lineNo = int(linePart[1:])
            fileName = fileName[0:-1 * linePart.length()].strip()
            if lineNo < 0:
                lineNo = -1

        if not os.path.isabs(fileName):
            currentFileName = self.__parentWidget.getFileName()
            if not currentFileName:
                logging.error("Relative path '" + fileName +
                              "' can be resolved only after the file is saved")
                return None, None
            currentDirName = os.path.dirname(currentFileName)
            fileName = os.path.normpath(currentDirName + os.path.sep + fileName)

        if not os.path.exists(fileName):
            logging.error('File not found: ' + fileName)
            return None, None
        if not os.path.isfile(fileName):
            logging.error('Not a file: ' + fileName)
            return None, None

        return fileName, lineNo

    def _onAnchorClicked(self, link):
        """Handles a URL click"""
        fileName, lineNo = self._resolveLink(link)
        if fileName:
            GlobalData().mainWindow.openFile(fileName, lineNo)

    def getScrollbarPositions(self):
        """Provides the scrollbar positions"""
        hScrollBar = self.horizontalScrollBar()
        hsbValue = hScrollBar.value() if hScrollBar else 0

        vScrollBar = self.verticalScrollBar()
        vsbValue = vScrollBar.value() if vScrollBar else 0
        return hsbValue, vsbValue

    def setScrollbarPositions(self, hPos, vPos):
        """Sets the scrollbar positions for the view"""
        hsb = self.horizontalScrollBar()
        if hsb:
            hsb.setValue(hPos)
        vsb = self.verticalScrollBar()
        if vsb:
            vsb.setValue(vPos)

    def loadResource(self, resourceType, resourceURL):
        """Overloaded; by default the remote pixmaps are not loaded"""
        if resourceType == QTextDocument.ImageResource:
            url = resourceURL.toString()
            currentFileName = self.__parentWidget.getFileName()
            if currentFileName:
                currentDir = os.path.dirname(currentFileName) + os.path.sep
                if url.startswith(currentDir):
                    url = url.replace(currentDir, '', 1)
            lowerUrl = url.lower()
            if lowerUrl.startswith('http:/') or lowerUrl.startswith('https:/'):
                if not lowerUrl.startswith('http://') and \
                   not lowerUrl.startswith('https://'):
                    url = url.replace(':/', '://', 1)
                fName = Settings().webResourceCache.getResource(
                    url, self.__parentWidget.getUUID())
                if fName is not None:
                    try:
                        return QPixmap(fName)
                    except Exception as exc:
                        logging.error('Cannot use the image from ' + fName +
                                      ': ' + str(exc))
                return None
        return TextViewer.loadResource(self, resourceType, resourceURL)

    def onResourceSaved(self, url, uuid, fName):
        """Triggered when a pixmap is received asynchronously"""
        if uuid == self.__parentWidget.getUUID():
            # Note: it is a hack! If the image is received after the document
            # is showed first time then its layout is wrong - not enough space
            # for the image and only a portion of the picture is shown.
            # The document re-layouting is required but there is no way to do
            # it directly. So there is this not-changing-anything call
            # which leads to re-layouting (update() does not help)
            # See here:
            # https://www.qtcentre.org/threads/6744-QTextEdit-and-delayed-image-loading
            self.setLineWrapColumnOrWidth(0)


class MDTopBar(QFrame):

    """MD widget top bar at the top"""

    STATE_OK_UTD = 0        # Parsed OK, MD up to date
    STATE_OK_CHN = 1        # Parsed OK, MD changed
    STATE_BROKEN_UTD = 2    # Parsed with errors, MD up to date
    STATE_BROKEN_CHN = 3    # Parsed with errors, MD changed
    STATE_UNKNOWN = 4

    def __init__(self, parent):
        QFrame.__init__(self, parent)
        self.__infoIcon = None
        self.__warningsIcon = None
        self.__layout = None
        self.__createLayout()
        self.__currentIconState = self.STATE_UNKNOWN

    def __createLayout(self):
        """Creates the layout"""
        self.setFixedHeight(24)
        self.__layout = QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)

        # Create info icon
        self.__infoIcon = QLabel()
        self.__infoIcon.setPixmap(getPixmap('cfunknown.png'))
        self.__layout.addWidget(self.__infoIcon)

        self.__warningsIcon = QLabel()
        self.__warningsIcon.setPixmap(getPixmap('cfwarning.png'))
        self.__layout.addWidget(self.__warningsIcon)

        self.clearWarnings()

        self.__spacer = QWidget()
        self.__spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.__spacer.setMinimumWidth(0)
        self.__layout.addWidget(self.__spacer)

    def clearWarnings(self):
        """Clears the warnings"""
        self.__warningsIcon.setVisible(False)
        self.__warningsIcon.setToolTip("")

    def setWarnings(self, warnings):
        """Sets the warnings"""
        self.__warningsIcon.setToolTip(
            'Markdown parser warnings:\n' + '\n'.join(warnings))
        self.__warningsIcon.setVisible(True)

    def clearErrors(self):
        """Clears all the errors"""
        self.__infoIcon.setToolTip('')

    def setErrors(self, errors):
        """Sets the errors"""
        self.__infoIcon.setToolTip(
            'Markdown parser errors:\n' + '\n'.join(errors))

    def updateInfoIcon(self, state):
        """Updates the information icon"""
        if state == self.__currentIconState:
            return

        if state == self.STATE_OK_UTD:
            self.__infoIcon.setPixmap(getPixmap('cfokutd.png'))
            self.__infoIcon.setToolTip("Markdown render is up to date")
            self.__currentIconState = self.STATE_OK_UTD
        elif state == self.STATE_OK_CHN:
            self.__infoIcon.setPixmap(getPixmap('cfokchn.png'))
            self.__infoIcon.setToolTip("Markdown render is not up to date; "
                                       "will be updated on idle")
            self.__currentIconState = self.STATE_OK_CHN
        elif state == self.STATE_BROKEN_UTD:
            self.__infoIcon.setPixmap(getPixmap('cfbrokenutd.png'))
            self.__infoIcon.setToolTip("Markdown render might be invalid "
                                       "due to invalid python code")
            self.__currentIconState = self.STATE_BROKEN_UTD
        elif state == self.STATE_BROKEN_CHN:
            self.__infoIcon.setPixmap(getPixmap('cfbrokenchn.png'))
            self.__infoIcon.setToolTip("Markdown render might be invalid; "
                                       "will be updated on idle")
            self.__currentIconState = self.STATE_BROKEN_CHN
        else:
            # STATE_UNKNOWN
            self.__infoIcon.setPixmap(getPixmap('cfunknown.png'))
            self.__infoIcon.setToolTip("Markdown render state is unknown")
            self.__currentIconState = self.STATE_UNKNOWN

    def getCurrentState(self):
        """Provides the current state"""
        return self.__currentIconState

    def resizeEvent(self, event):
        """Editor has resized"""
        QFrame.resizeEvent(self, event)


class MDWidget(QWidget):

    """The MD rendered content widget which goes along with the text editor"""

    sigEscapePressed = pyqtSignal()

    def __init__(self, editor, parent):
        QWidget.__init__(self, parent)

        self.setVisible(False)

        self.__editor = editor
        self.__parentWidget = parent
        self.__connected = False

        hLayout = QHBoxLayout()
        hLayout.setContentsMargins(0, 0, 0, 0)
        hLayout.setSpacing(0)

        vLayout = QVBoxLayout()
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(0)

        # Make pylint happy
        self.__toolbar = None
        self.__topBar = None

        # Create the update timer
        self.__updateTimer = QTimer(self)
        self.__updateTimer.setSingleShot(True)
        self.__updateTimer.timeout.connect(self.process)

        vLayout.addWidget(self.__createTopBar())
        vLayout.addWidget(self.__createMDView())

        hLayout.addLayout(vLayout)
        hLayout.addWidget(self.__createToolbar())
        self.setLayout(hLayout)

        # Connect to the change file type signal
        self.__mainWindow = GlobalData().mainWindow
        editorsManager = self.__mainWindow.em
        editorsManager.sigFileTypeChanged.connect(self.__onFileTypeChanged)

    def __createToolbar(self):
        """Creates the toolbar"""
        self.__toolbar = QToolBar(self)
        self.__toolbar.setOrientation(Qt.Vertical)
        self.__toolbar.setMovable(False)
        self.__toolbar.setAllowedAreas(Qt.RightToolBarArea)
        self.__toolbar.setIconSize(QSize(16, 16))
        self.__toolbar.setFixedWidth(30)
        self.__toolbar.setContentsMargins(0, 0, 0, 0)

        # Some control buttons could be added later
        printButton = QAction(getIcon('printer.png'), 'Print', self)
        printButton.triggered.connect(self.__onPrint)
        self.__toolbar.addAction(printButton)

        return self.__toolbar

    def __createTopBar(self):
        """Creates the top bar"""
        self.__topBar = MDTopBar(self)
        return self.__topBar

    def __createMDView(self):
        """Creates the graphics view"""
        self.mdView = MDViewer(self)
        self.mdView.sigEscapePressed.connect(self.__onEsc)
        return self.mdView

    def __onPrint(self):
        """Print the markdown page"""
        dialog = QPrintDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            printer = dialog.printer()
            self.mdView.print_(printer)

    def __onEsc(self):
        """Triggered when Esc is pressed"""
        self.sigEscapePressed.emit()

    def process(self):
        """Parses the content and displays the results"""
        if not self.__connected:
            self.__connectEditorSignals()

        renderedText, errors, warnings = renderMarkdown(self.__editor.text,
                                                        self.getFileName())
        if errors:
            self.__topBar.updateInfoIcon(self.__topBar.STATE_BROKEN_UTD)
            self.__topBar.setErrors(errors)
            return
        if renderedText is None:
            self.__topBar.updateInfoIcon(self.__topBar.STATE_BROKEN_UTD)
            self.__topBar.setErrors(['Unknown markdown rendering error'])
            return

        # That will clear the error tooltip as well
        self.__topBar.updateInfoIcon(self.__topBar.STATE_OK_UTD)

        if warnings:
            self.__topBar.setWarnings(warnings)
        else:
            self.__topBar.clearWarnings()

        hsbValue, vsbValue = self.getScrollbarPositions()
        self.mdView.setHtml(renderedText)
        self.setScrollbarPositions(hsbValue, vsbValue)

    def __onFileTypeChanged(self, fileName, uuid, newFileType):
        """Triggered when a buffer content type has changed"""
        if self.getUUID() != uuid:
            return

        if not isMarkdownMime(newFileType):
            self.__disconnectEditorSignals()
            self.__updateTimer.stop()
            self.setVisible(False)
            self.__topBar.updateInfoIcon(self.__topBar.STATE_UNKNOWN)
            return

        # Update the bar and show it
        self.setVisible(True)
        self.process()

        # The buffer type change event comes when the content is loaded first
        # time. So this is a good point to restore the position
        _, _, _, hPos, vPos = getFilePosition(fileName)
        self.setScrollbarPositions(hPos, vPos)

    def __connectEditorSignals(self):
        """When it is a python file - connect to the editor signals"""
        if not self.__connected:
            self.__editor.cursorPositionChanged.connect(
                self.__cursorPositionChanged)
            self.__editor.textChanged.connect(self.__onBufferChanged)
            self.__connected = True

    def __disconnectEditorSignals(self):
        """Disconnect the editor signals when the file is not a python one"""
        if self.__connected:
            self.__editor.cursorPositionChanged.disconnect(
                self.__cursorPositionChanged)
            self.__editor.textChanged.disconnect(self.__onBufferChanged)
            self.__connected = False

    def __cursorPositionChanged(self):
        """Cursor position changed"""
        # The timer should be reset only in case if the redrawing was delayed
        if self.__updateTimer.isActive():
            self.__updateTimer.stop()
            self.__updateTimer.start(IDLE_TIMEOUT)

    def __onBufferChanged(self):
        """Triggered to update status icon and to restart the timer"""
        self.__updateTimer.stop()
        if self.__topBar.getCurrentState() in [self.__topBar.STATE_OK_UTD,
                                               self.__topBar.STATE_OK_CHN,
                                               self.__topBar.STATE_UNKNOWN]:
            self.__topBar.updateInfoIcon(self.__topBar.STATE_OK_CHN)
        else:
            self.__topBar.updateInfoIcon(self.__topBar.STATE_BROKEN_CHN)
        self.__updateTimer.start(IDLE_TIMEOUT)

    def redrawNow(self):
        """Redraw the diagram regardless of the timer"""
        if self.__updateTimer.isActive():
            self.__updateTimer.stop()
        self.process()

    def getScrollbarPositions(self):
        """Provides the scrollbar positions"""
        return self.mdView.getScrollbarPositions()

    def setScrollbarPositions(self, hPos, vPos):
        """Sets the scrollbar positions for the view"""
        self.mdView.setScrollbarPositions(hPos, vPos)

    def getFileName(self):
        return self.__parentWidget.getFileName()

    def getUUID(self):
        return self.__parentWidget.getUUID()

