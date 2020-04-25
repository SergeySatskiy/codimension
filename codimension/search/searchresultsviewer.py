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

import logging
from uuid import uuid1
from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from utils.fileutils import getFileProperties
from utils.project import CodimensionProject
from utils.misc import getLocaleDateTime
from ui.qt import (Qt, QSize, QToolBar, QBrush, QHBoxLayout, QWidget, QAction,
                   QLabel, QFrame, QTreeWidget, QApplication, QTreeWidgetItem,
                   QHeaderView, QPalette, QColor, QStackedWidget, QSizePolicy,
                   QVBoxLayout)
from ui.itemdelegates import NoOutlineHeightDelegate
from ui.spacers import ToolBarExpandingSpacer
from ui.labels import HeaderLabel, HeaderFitLabel
from .matchtooltip import MatchTooltip
from .occurrencesprovider import OccurrencesSearchProvider


MAX_RESULTS = 32

# Global tooltip instance
searchTooltip = MatchTooltip()


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
            searchTooltip.setInside(True)

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


class SearchResultsTreeWidget(QTreeWidget):

    """Tree widget derivation to intercept the fact that the mouse cursor
       left the widget
    """

    lastEntered = None

    def __init__(self, parent=None):
        QTreeWidget.__init__(self, parent)
        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(True)
        self.setItemsExpandable(True)
        self.setUniformRowHeights(True)
        self.setItemDelegate(NoOutlineHeightDelegate(4))
        headerLabels = ['File name / line', '', 'Text']
        self.setHeaderLabels(headerLabels)
        self.setMouseTracking(True)

        self.resetCache()

        self.itemActivated.connect(self.__resultActivated)
        self.itemClicked.connect(self.__resultClicked)
        self.itemEntered.connect(self.__itemEntered)

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
        searchTooltip.setInside(False)

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
        item.setBackground(2, brush)
        childIndex = item.childCount() - 1
        while childIndex >= 0:
            childItem = item.child(childIndex)
            childItem.setModified(True)
            if searchTooltip.item == childItem:
                searchTooltip.setModified(True)
            childIndex -= 1

    @staticmethod
    def __resultActivated(item, column):
        """Handles the double click (or Enter) on a match"""
        del column  # unused argument
        if isinstance(item, MatchTableItem):
            try:
                fileName = item.parent().data(0, Qt.DisplayRole)
                lineNumber = int(item.data(0, Qt.DisplayRole))
                GlobalData().mainWindow.openFile(fileName, lineNumber)
                hideSearchTooltip()
            except Exception as exc:
                logging.error(str(exc))

    @staticmethod
    def __resultClicked(item, column):
        """Handles the single click"""
        del item    # unused argument
        del column  # unused argument
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
        searchTooltip.setCellHeight(self.visualItemRect(item).height())

        if self.lastEntered != item or not searchTooltip.isInside():
            item.itemEntered()
            self.lastEntered = item



class ResultsViewerWidget(QWidget):

    """A header plus a tree widget"""

    def __init__(self, providerId, results, parameters, searchId, parent):
        QWidget.__init__(self, parent)

        self.__providerId = providerId
        self.__parameters = parameters
        self.searchId = searchId
        self.selectedItem = None
        self.__removeItemButton = parent.removeItemButton

        self.resultsTree = SearchResultsTreeWidget()
        self.resultsTree.itemSelectionChanged.connect(
            self.__selectionChanged)

        self.indicator = HeaderLabel()
        self.providerLabel = HeaderLabel(
            GlobalData().searchProviders[providerId].getName())
        self.providerLabel.setToolTip('Results provider')
        self.timestampLabel = HeaderLabel()
        self.timestampLabel.setToolTip('Search timestamp')

        self.__labelLayout = QHBoxLayout()
        self.__labelLayout.setContentsMargins(0, 0, 0, 0)
        self.__labelLayout.setSpacing(4)
        self.__labelLayout.addWidget(self.indicator)
        self.__labelLayout.addWidget(self.providerLabel)

        # There could be many labels with the search parameters
        for item in GlobalData().searchProviders[providerId].serialize(parameters):
            paramLabel = HeaderFitLabel()
            paramLabel.setText('%s: %s' % item)
            paramLabel.setAlignment(Qt.AlignLeft)
            paramLabel.setSizePolicy(QSizePolicy.Expanding,
                                     QSizePolicy.Fixed)
            self.__labelLayout.addWidget(paramLabel)

        self.__labelLayout.addWidget(self.timestampLabel)

        self.__vLayout = QVBoxLayout()
        self.__vLayout.setContentsMargins(0, 0, 0, 0)
        self.__vLayout.setSpacing(4)
        self.__vLayout.addLayout(self.__labelLayout)
        self.__vLayout.addWidget(self.resultsTree)

        self.setLayout(self.__vLayout)
        self.populate(results)

    def populate(self, results):
        """Populates data in the tree widget"""
        self.clear()
        self.timestampLabel.setText(getLocaleDateTime())

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
            self.resultsTree.addTopLevelItem(fileItem)

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
        self.resultsTree.setHeaderLabels(headerLabels)

        # Resizing the table
        self.resultsTree.header().resizeSections(QHeaderView.ResizeToContents)
        self.resultsTree.header().setSectionResizeMode(1, QHeaderView.Fixed)
        self.resultsTree.header().resizeSection(1, 30)

        self.resultsTree.buildCache()

    def updateIndicator(self, own, total):
        """Updates the indicator label and tooltip"""
        self.indicator.setText('%d of %d' % (own, total))
        self.indicator.setToolTip('Search result %d out of %d' %
                                  (own, total))

    def clear(self):
        """Clean up"""
        self.resultsTree.resetCache()
        self.resultsTree.clear()
        self.selectedItem = None

    def __selectionChanged(self):
        """Selection of an item changed"""
        selected = list(self.resultsTree.selectedItems())
        if selected:
            self.selectedItem = selected[0]
            self.__removeItemButton.setEnabled(True)
        else:
            self.selectedItem = None
            self.__removeItemButton.setEnabled(False)

    def removeSelectedItem(self):
        """Removes the selected item"""
        if self.selectedItem is None:
            return

        if isinstance(self.selectedItem, MatchTableFileItem):
            # This is a top level item
            topItemIndex = self.resultsTree.indexOfTopLevelItem(
                self.selectedItem)
            self.resultsTree.takeTopLevelItem(topItemIndex)
        else:
            # This is a file item, i.e. a child
            parentItem = self.selectedItem.parent()
            childIndex = parentItem.indexOfChild(self.selectedItem)
            parentItem.takeChild(childIndex)
            if parentItem.childCount() == 0:
                # The top level item needs to be deleted too
                topItemIndex = self.resultsTree.indexOfTopLevelItem(
                    parentItem)
                self.resultsTree.takeTopLevelItem(topItemIndex)

        if self.resultsTree.topLevelItemCount() > 0:
            self.__updateCounters()

    def __updateCounters(self):
        """Updates the counters after a match is deleted"""
        total = 0
        fileCount = self.resultsTree.topLevelItemCount()
        for index in range(fileCount):
            topLevelItem = self.resultsTree.topLevelItem(index)
            matchCount = topLevelItem.childCount()
            if matchCount == 1:
                matchText = " (1 match)"
            else:
                matchText = " (" + str(matchCount) + " matches)"
            total += matchCount
            topLevelItem.setText(2, matchText)

        headerLabels = ["File name / line (total files: " +
                        str(fileCount) + ")",
                        '',
                        "Text (total matches: " + str(total) + ")"]
        self.resultsTree.setHeaderLabels(headerLabels)

    def doAgain(self, resultsViewer):
        """Performs the same search again"""
        GlobalData().searchProviders[self.__providerId].searchAgain(
            self.searchId, self.__parameters, resultsViewer)

    def canDoAgain(self):
        """Tells if the do again functionality is available"""
        if self.__providerId == OccurrencesSearchProvider.getName():
            # There are too many cases when it is problematic to do again
            # jedi needs to have a source code and a cursor position in it
            # however, at least following may brake the search:
            # - the buffer has been changed (could be tracked)
            # - the file was closed so there is no more editor (could be
            #   reloaded)
            # - the file was changed outside of the ide (cannot be tracked)
            # - the file is changed between the ide sessions when the feature
            #   of saving/restoring results is implemented (cannot be tracked)
            # So for now the redo is just disabled for this provider
            return False
        return True


class SearchResultsViewer(QWidget):

    """Search results viewer tab widget"""

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.__results = QStackedWidget(self)

        self.__bufferChangeConnected = False

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

        self.__createLayout(parent)
        self.__updateButtonsStatus()

        GlobalData().project.sigProjectChanged.connect(self.__onProjectChanged)

    def __createLayout(self, parent):
        """Creates the toolbar and layout"""
        del parent  # unused argument

        # Buttons etc.
        self.clearButton = QAction(getIcon('trash.png'),
                                   'Delete current results', self)
        self.clearButton.triggered.connect(self.__clear)

        self.prevButton = QAction(getIcon('1leftarrow.png'),
                                  'Previous results', self)
        self.prevButton.triggered.connect(self.__previous)

        self.nextButton = QAction(getIcon('1rightarrow.png'),
                                  'Next results', self)
        self.nextButton.triggered.connect(self.__next)

        self.doAgainButton = QAction(getIcon('searchagain.png'),
                                     'Do again', self)
        self.doAgainButton.triggered.connect(self.__doAgain)

        self.removeItemButton = QAction(getIcon('delitem.png'),
                                        'Remove currently selected item (Del)',
                                        self)
        self.removeItemButton.triggered.connect(self.__removeItem)

        # The toolbar
        self.toolbar = QToolBar(self)
        self.toolbar.setOrientation(Qt.Vertical)
        self.toolbar.setMovable(False)
        self.toolbar.setAllowedAreas(Qt.RightToolBarArea)
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setFixedWidth(28)
        self.toolbar.setContentsMargins(0, 0, 0, 0)

        self.toolbar.addAction(self.prevButton)
        self.toolbar.addAction(self.nextButton)
        self.toolbar.addAction(self.doAgainButton)
        self.toolbar.addWidget(ToolBarExpandingSpacer(self.toolbar))
        self.toolbar.addAction(self.removeItemButton)
        self.toolbar.addAction(self.clearButton)

        self.__hLayout = QHBoxLayout()
        self.__hLayout.setContentsMargins(0, 0, 0, 0)
        self.__hLayout.setSpacing(0)
        self.__hLayout.addWidget(self.toolbar)
        self.__hLayout.addWidget(self.__noneLabel)
        self.__hLayout.addWidget(self.__results)
        self.__results.hide()

        self.setLayout(self.__hLayout)

    def __isReportShown(self):
        """True is any of the reports is shown"""
        return self.__results.count() > 0

    def getResultsViewer(self):
        """Provides a reference to the results tree"""
        return self.__results

    def __updateButtonsStatus(self):
        """Updates the buttons status"""
        if self.__isReportShown():
            index = self.__results.currentIndex()
            widget = self.__results.currentWidget()
            self.prevButton.setEnabled(index > 0)
            self.nextButton.setEnabled(index < self.__results.count() - 1)
            self.doAgainButton.setEnabled(widget.canDoAgain())
            self.removeItemButton.setEnabled(widget.selectedItem is not None)
            self.clearButton.setEnabled(True)
        else:
            self.prevButton.setEnabled(False)
            self.nextButton.setEnabled(False)
            self.doAgainButton.setEnabled(False)
            self.removeItemButton.setEnabled(False)
            self.clearButton.setEnabled(False)

    def __updateIndicators(self):
        """Updates all the indicators"""
        total = self.__results.count()
        for index in range(total):
            self.__results.widget(index).updateIndicator(index + 1, total)

    def setFocus(self):
        """Overridden setFocus"""
        self.__hLayout.setFocus()

    def __onProjectChanged(self, what):
        """Triggered when a project is changed"""
        if what == CodimensionProject.CompleteProject:
            self.__saveProjectResults()
            self.__populateForProject()

    def __connectBufferChange(self):
        """Connects the sigBufferChange"""
        if not self.__bufferChangeConnected:
            self.__bufferChangeConnected = True
            mainWindow = GlobalData().mainWindow
            editorsManager = mainWindow.editorsManagerWidget.editorsManager
            editorsManager.sigBufferModified.connect(self.onBufferModified)

    def __disconnectBufferChange(self):
        """Disconnects the sigBufferModified signal"""
        if self.__bufferChangeConnected:
            self.__bufferChangeConnected = False
            mainWindow = GlobalData().mainWindow
            editorsManager = mainWindow.editorsManagerWidget.editorsManager
            editorsManager.sigBufferModified.disconnect(self.onBufferModified)

    def onBufferModified(self, fileName, uuid):
        """Triggered when a buffer is modified"""
        for index in range(self.__results.count()):
            self.__results.widget(index).resultsTree.onBufferModified(
                fileName, uuid)

    def __previous(self):
        """Switch to the previous results"""
        if self.__isReportShown():
            index = self.__results.currentIndex()
            if index > 0:
                self.__results.setCurrentIndex(index - 1)
                self.__updateButtonsStatus()

    def __next(self):
        """Switch to the next results"""
        if self.__isReportShown():
            index = self.__results.currentIndex()
            if index < self.__results.count() - 1:
                self.__results.setCurrentIndex(index + 1)
                self.__updateButtonsStatus()

    def keyPressEvent(self, event):
        """Del key processing"""
        if event.key() == Qt.Key_Delete:
            event.accept()
            self.__removeItem()
        else:
            QWidget.keyPressEvent(self, event)

    def __removeItem(self):
        """Removes one entry of the search"""
        widget = self.__results.currentWidget()
        if widget.selectedItem is None:
            return

        widget.removeSelectedItem()
        if widget.resultsTree.topLevelItemCount() == 0:
            # The last result, need to remove the search result
            self.__clear()
        else:
            self.__updateButtonsStatus()

    def __clear(self):
        """Clears the content of the vertical layout"""
        if not self.__isReportShown():
            return

        index = self.__results.currentIndex()
        widget = self.__results.currentWidget()
        widget.clear()

        if self.__results.count() == 1:
            self.__results.hide()
            self.__noneLabel.show()
            self.__disconnectBufferChange()

        self.__results.removeWidget(widget)
        widget.deleteLater()

        if self.__results.count() > 0:
            if index >= self.__results.count():
                index -= 1
            self.__results.setCurrentIndex(index)

        self.__updateButtonsStatus()
        self.__updateIndicators()

    def __doAgain(self):
        """Performs the action once again"""
        if self.__isReportShown():
            self.__results.currentWidget().doAgain(self)

    def showReport(self, providerId, results, parameters, searchId=None):
        """Shows the find in files results"""
        # Memorize the screen width
        searchTooltip.setScreenWidth(
            GlobalData().application.desktop().screenGeometry().width())

        if searchId is None:
            resultWidget = ResultsViewerWidget(providerId, results,
                                               parameters,
                                               str(uuid1()), self)
            index = self.__results.addWidget(resultWidget)
        else:
            # Find the widget with this searchId
            found = False
            for index in range(self.__results.count()):
                if self.__results.widget(index).searchId == searchId:
                    found = True
                    break
            if not found:
                # add as a new one
                resultWidget = ResultsViewerWidget(providerId, results,
                                                   parameters,
                                                   str(uuid1()), self)
                index = self.__results.addWidget(resultWidget)
            else:
                # Repopulate it
                widget = self.__results.widget(index)
                widget.populate(results)

        self.__results.setCurrentIndex(index)

        # Show the complete information
        self.__noneLabel.hide()
        self.__results.show()

        self.__updateButtonsStatus()
        self.__updateIndicators()
        self.__connectBufferChange()

    def __populateForProject(self):
        """Load the project saved search results"""

    def __saveProjectResults(self):
        """Serialize to the disk the search results"""
        # Should not overwrite empty results when IDE is loaded

