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

"""Find in files viewer implementation"""

from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from utils.fileutils import getFileProperties
from utils.project import CodimensionProject
from utils.colorfont import getZoomedMonoFont
from .qt import (Qt, QSize, QTimer, QToolBar, QCursor, QBrush, QHBoxLayout,
                 QWidget, QAction, QLabel, QSizePolicy, QFrame,
                 QTreeWidget, QApplication, QTreeWidgetItem,
                 QHeaderView, QToolTip, QPalette, QColor, QVBoxLayout)
from .itemdelegates import NoOutlineHeightDelegate


cellHeight = 20     # default
screenWidth = 600   # default

# On slow network connections when XServer is used the cursor movement is
# delivered with a considerable delay which causes improper tooltip displaying.
# This global variable prevents improper displaying.
inside = False


class Tooltip(QFrame):

    """Custom tooltip"""

    def __init__(self):
        QFrame.__init__(self)

        # Avoid the border around the window
        self.setWindowFlags(Qt.SplashScreen |
                            Qt.WindowStaysOnTopHint |
                            Qt.X11BypassWindowManagerHint)

        # Make the frame nice looking
        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(2)

        self.info = None
        self.location = None
        self.__createLayout()

        # The item the tooltip is for
        self.item = None

        # The timer which shows the tooltip. The timer is controlled from
        # outside of the class.
        self.tooltipTimer = QTimer(self)
        self.tooltipTimer.setSingleShot(True)
        self.tooltipTimer.timeout.connect(self.__onTimer)

        self.startPosition = None

    def __createLayout(self):
        """Creates the tooltip layout"""
        verticalLayout = QVBoxLayout(self)
        verticalLayout.setContentsMargins(0, 0, 0, 0)

        self.info = QLabel()
        self.info.setAutoFillBackground(True)
        self.info.setFont(getZoomedMonoFont())
        self.info.setFrameShape(QFrame.StyledPanel)
        self.info.setStyleSheet('padding: 4px')
        verticalLayout.addWidget(self.info)

        self.location = QLabel()
        # verticalLayout.addWidget(self.location)

    def setText(self, text):
        """Sets the tooltip text"""
        self.info.setFont(getZoomedMonoFont())
        self.info.setText(text)

    def setLocation(self, text):
        """Sets the file name and line at the bottom"""
        self.location.setText(text)

    def setModified(self, status):
        """Sets the required tooltip background"""
        palette = self.info.palette()
        if status:
            # Reddish
            palette.setColor(QPalette.Background, QColor(255, 227, 227))
        else:
            # Blueish
            palette.setColor(QPalette.Background, QColor(224, 236, 255))
        self.info.setPalette(palette)

    def setItem(self, item):
        """Sets the item the tooltip is shown for"""
        self.item = item

    def __getTooltipPos(self):
        """Calculates the tooltip position - above the row"""
        pos = QCursor.pos()
        if pos.x() + self.sizeHint().width() >= screenWidth:
            pos.setX(screenWidth - self.sizeHint().width() - 2)
        pos.setY(pos.y() - cellHeight - 1 - self.sizeHint().height())
        return pos

    def __onTimer(self):
        """Triggered by the show tooltip timer"""
        currentPos = QCursor.pos()
        if abs(currentPos.x() - self.startPosition.x()) <= 2 and \
           abs(currentPos.y() - self.startPosition.y()) <= 2:
            # No movement since last time, show the tooltip
            self.show()
            return

        # There item has not been changed, but the position within it was
        # So restart the timer, but for shorter
        self.startPosition = currentPos
        self.tooltipTimer.start(400)

    def startShowTimer(self):
        """Memorizes the cursor position and starts the timer"""
        self.tooltipTimer.stop()
        self.startPosition = QCursor.pos()
        self.tooltipTimer.start(500)  # 0.5 sec

    def show(self):
        """Shows the tooltip at the proper position"""
        QToolTip.hideText()
        QApplication.processEvents()
        if inside:
            self.move(self.__getTooltipPos())
            self.raise_()
            QFrame.show(self)


# Global tooltip instance
searchTooltip = None


def hideSearchTooltip():
    """Hides the search results tooltip"""
    searchTooltip.tooltipTimer.stop()
    searchTooltip.hide()


class MatchTableItem(QTreeWidgetItem):

    """Match item"""

    def __init__(self, items, tooltip):
        items.insert(1, '')
        QTreeWidgetItem.__init__(self, items)
        self.__intColumn = 0
        self.__tooltip = tooltip
        self.__fileModified = False
        self.setIcon(1, getIcon('findtooltip.png'))

        # Memorize the screen width
        global screenWidth
        screenSize = GlobalData().application.desktop().screenGeometry()
        screenWidth = screenSize.width()

    def __lt__(self, other):
        """Integer or string custom sorting"""
        sortColumn = self.treeWidget().sortColumn()
        if sortColumn == self.__intColumn:
            return int(self.text(sortColumn)) < \
                   int(other.text(sortColumn))
        return self.text(sortColumn) < other.text(sortColumn)

    def setModified(self, status):
        """Sets the modified flag"""
        self.__fileModified = status

    def __updateTooltipProperties(self):
        """Updates all the tooltip properties"""
        searchTooltip.setItem(self)
        searchTooltip.setModified(self.__fileModified)
        searchTooltip.setText(self.__tooltip)

        fileName = self.parent().data(0, Qt.DisplayRole)
        lineNumber = self.data(0, Qt.DisplayRole)
        searchTooltip.setLocation(" " + fileName + ":" + lineNumber)

    def itemEntered(self):
        """Triggered when mouse cursor entered the match"""
        if self.__tooltip:
            global inside
            inside = True

            if searchTooltip.isVisible():
                hideSearchTooltip()
                self.__updateTooltipProperties()
                searchTooltip.show()
            else:
                searchTooltip.startShowTimer()
                self.__updateTooltipProperties()


class MatchTableFileItem(QTreeWidgetItem):

    """Match file item"""

    def __init__(self, items, uuid):
        QTreeWidgetItem.__init__(self, items)
        self.uuid = uuid


class FindResultsTreeWidget(QTreeWidget):

    """Tree widget derivation to intercept the fact that the mouse cursor
       left the widget
    """

    def __init__(self, parent=None):
        QTreeWidget.__init__(self, parent)
        self.resetCache()

    def resetCache(self):
        """Resets the caches"""
        self.__fNameCache = set()
        self.__uuidCache = set()

    def buildCache(self):
        """Builds the caches"""
        index = self.topLevelItemCount() - 1
        while index >= 0:
            item = self.topLevelItem(index)
            fileName = item.data(0, Qt.DisplayRole)
            self.__fNameCache.add(fileName)
            self.__uuidCache.add(str(item.uuid))
            index -= 1

    def leaveEvent(self, event):
        """Triggered when the cursor leaves the find results tree"""
        global inside
        inside = False

        QApplication.processEvents()
        hideSearchTooltip()
        QTreeWidget.leaveEvent(self, event)

    def onBufferModified(self, fileName, uuid):
        """Triggered when a buffer is modified"""
        uuid = str(uuid)
        fileName = str(fileName)
        if uuid in self.__uuidCache:
            self.__markByUUID(uuid)
            self.__uuidCache.remove(uuid)
            return
        if fileName in self.__fNameCache:
            self.__markByFileName(fileName)
            self.__fNameCache.remove(fileName)

    def __markByUUID(self, uuid):
        """Marks an item modified basing on the editor UUID"""
        index = self.topLevelItemCount() - 1
        while index >= 0:
            item = self.topLevelItem(index)
            if item.uuid == uuid:
                self.__markItem(item)
                break
            index -= 1

    def __markByFileName(self, fileName):
        """Marks an item modified basing on the file name"""
        index = self.topLevelItemCount() - 1
        while index >= 0:
            item = self.topLevelItem(index)
            if item.data(0, Qt.DisplayRole) == fileName:
                self.__markItem(item)
                break
            index -= 1

    @staticmethod
    def __markItem(item):
        """Marks a single item modified"""
        brush = QBrush(QColor(255, 227, 227))
        item.setBackground(0, brush)
        item.setBackground(1, brush)
        childIndex = item.childCount() - 1
        while childIndex >= 0:
            childItem = item.child(childIndex)
            childItem.setModified(True)
            if searchTooltip.item == childItem:
                searchTooltip.setModified(True)
            childIndex -= 1


class FindInFilesViewer(QWidget):

    """Find in files viewer tab widget"""

    lastEntered = None

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        global searchTooltip
        searchTooltip = Tooltip()

        self.__reportRegexp = None
        self.__reportResults = []
        self.__reportShown = False
        self.__bufferChangeconnected = False

        # Prepare members for reuse
        self.__noneLabel = QLabel("\nNo results available")

        self.__noneLabel.setFrameShape(QFrame.StyledPanel)
        self.__noneLabel.setAlignment(Qt.AlignHCenter)
        self.__headerFont = self.__noneLabel.font()
        self.__headerFont.setPointSize(self.__headerFont.pointSize() + 4)
        self.__noneLabel.setFont(self.__headerFont)
        self.__noneLabel.setAutoFillBackground(True)
        noneLabelPalette = self.__noneLabel.palette()
        noneLabelPalette.setColor(QPalette.Background,
                                  GlobalData().skin['nolexerPaper'])
        self.__noneLabel.setPalette(noneLabelPalette)

        # Keep pylint happy
        self.clearButton = None

        self.__createLayout(parent)

        self.__updateButtonsStatus()

        GlobalData().project.sigProjectChanged.connect(self.__onProjectChanged)

    def __createLayout(self, parent):
        """Creates the toolbar and layout"""
        del parent  # unused argument

        # Buttons
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.clearButton = QAction(getIcon('trash.png'), 'Clear', self)
        self.clearButton.triggered.connect(self.__clear)

        # The toolbar
        self.toolbar = QToolBar(self)
        self.toolbar.setOrientation(Qt.Vertical)
        self.toolbar.setMovable(False)
        self.toolbar.setAllowedAreas(Qt.RightToolBarArea)
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setFixedWidth(28)
        self.toolbar.setContentsMargins(0, 0, 0, 0)

        self.toolbar.addWidget(spacer)
        self.toolbar.addAction(self.clearButton)

        self.__resultsTree = FindResultsTreeWidget()
        self.__resultsTree.setAlternatingRowColors(True)
        self.__resultsTree.setRootIsDecorated(True)
        self.__resultsTree.setItemsExpandable(True)
        self.__resultsTree.setUniformRowHeights(True)
        self.__resultsTree.setItemDelegate(NoOutlineHeightDelegate(4))
        headerLabels = ['File name / line', '', 'Text']
        self.__resultsTree.setHeaderLabels(headerLabels)
        self.__resultsTree.itemActivated.connect(self.__resultActivated)
        self.__resultsTree.itemClicked.connect(self.__resultClicked)
        self.__resultsTree.setMouseTracking(True)
        self.__resultsTree.itemEntered.connect(self.__itemEntered)
        self.__resultsTree.hide()

        self.__hLayout = QHBoxLayout()
        self.__hLayout.setContentsMargins(0, 0, 0, 0)
        self.__hLayout.setSpacing(0)
        self.__hLayout.addWidget(self.toolbar)
        self.__hLayout.addWidget(self.__noneLabel)
        self.__hLayout.addWidget(self.__resultsTree)

        self.setLayout(self.__hLayout)

    def getResultsTree(self):
        """Provides a reference to the results tree"""
        return self.__resultsTree

    def __updateButtonsStatus(self):
        """Updates the buttons status"""
        self.clearButton.setEnabled(self.__reportShown)

    def setFocus(self):
        """Overridden setFocus"""
        self.__hLayout.setFocus()

    def __onProjectChanged(self, what):
        """Triggered when a project is changed"""
        if what == CodimensionProject.CompleteProject:
            self.__clear()

    def __clear(self):
        """Clears the content of the vertical layout"""
        if not self.__reportShown:
            return

        # Disconnect the buffer change signal if it is connected
        if self.__bufferChangeconnected:
            self.__bufferChangeconnected = False
            mainWindow = GlobalData().mainWindow
            editorsManager = mainWindow.editorsManagerWidget.editorsManager
            editorsManager.sigBufferModified.disconnect(
                self.__resultsTree.onBufferModified)

        self.__resultsTree.resetCache()
        self.__resultsTree.clear()
        self.__resultsTree.hide()
        self.__noneLabel.show()

        self.__reportRegexp = None
        self.__reportResults = []
        self.__reportShown = False
        self.__updateButtonsStatus()

    def showReport(self, regexp, results):
        """Shows the find in files results"""
        self.__clear()
        self.__noneLabel.hide()

        self.__reportRegexp = regexp
        self.__reportResults = results

        # Add the complete information
        totalMatched = 0
        for item in results:
            matched = len(item.matches)
            totalMatched += matched
            if matched == 1:
                matchText = " (1 match)"
            else:
                matchText = " (" + str(matched) + " matches)"
            columns = [item.fileName, '', matchText]
            fileItem = MatchTableFileItem(columns, item.bufferUUID)
            _, icon, _ = getFileProperties(item.fileName)
            fileItem.setIcon(0, icon)
            if item.tooltip != "":
                fileItem.setToolTip(0, item.tooltip)
            self.__resultsTree.addTopLevelItem(fileItem)

            # Matches
            for match in item.matches:
                columns = [str(match.line), match.text]
                matchItem = MatchTableItem(columns, match.tooltip)
                fileItem.addChild(matchItem)
            fileItem.setExpanded(True)

        # Update the header with the total number of matches
        headerLabels = ["File name / line (total files: " +
                        str(len(results)) + ")",
                        '',
                        "Text (total matches: " + str(totalMatched) + ")"]
        self.__resultsTree.setHeaderLabels(headerLabels)

        # Resizing the table
        self.__resultsTree.header().resizeSections(
            QHeaderView.ResizeToContents)
        self.__resultsTree.header().setSectionResizeMode(1, QHeaderView.Fixed)
        self.__resultsTree.header().resizeSection(1, 30)

        # Show the complete information
        self.__resultsTree.show()
        self.__resultsTree.buildCache()

        self.__reportShown = True
        self.__updateButtonsStatus()

        # Connect the buffer change signal if not connected yet
        if not self.__bufferChangeconnected:
            self.__bufferChangeconnected = True
            mainWindow = GlobalData().mainWindow
            editorsManager = mainWindow.editorsManagerWidget.editorsManager
            editorsManager.sigBufferModified.connect(
                self.__resultsTree.onBufferModified)

    @staticmethod
    def __resultClicked(item, column):
        """Handles the single click"""
        del item    # unused argument
        del column  # unused argument
        hideSearchTooltip()

    def __resultActivated(self, item, column):
        """Handles the double click (or Enter) on a match"""
        del column  # unused argument
        if isinstance(item, MatchTableItem):
            fileName = item.parent().data(0, Qt.DisplayRole)
            lineNumber = int(item.data(0, Qt.DisplayRole))
            GlobalData().mainWindow.openFile(fileName, lineNumber)
            hideSearchTooltip()

    def __itemEntered(self, item, column):
        """Triggered when the mouse cursor entered a row"""
        if not isinstance(item, MatchTableItem):
            self.lastEntered = item
            hideSearchTooltip()
            return

        if column != 1:
            # Show the tooltip only for the column with results
            self.lastEntered = None
            hideSearchTooltip()
            return

        # Memorize the row height for proper tooltip displaying later
        global cellHeight
        cellHeight = self.__resultsTree.visualItemRect(item).height()

        if self.lastEntered != item or not inside:
            item.itemEntered()
            self.lastEntered = item
