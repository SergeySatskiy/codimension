# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017 Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Profiling results as a table"""

import logging
import os.path
from ui.qt import (Qt, pyqtSignal, QCursor,
                   QTreeWidgetItem, QTreeWidget, QLabel, QWidget, QVBoxLayout,
                   QHeaderView, QMenu, QAbstractItemView, QSizePolicy)
from ui.itemdelegates import NoOutlineHeightDelegate
from utils.globals import GlobalData
from utils.pixmapcache import getIcon
from utils.colorfont import getLabelStyle


FLOAT_FORMAT = "%8.6f"
MAX_CALLS_IN_TOOLTIP = 32

OUTSIDE_COL_INDEX = 0
CALLS_COL_INDEX = 1
TOTAL_COL_INDEX = 2
TOTALPERCALL_COL_INDEX = 3
CUM_COL_INDEX = 4
CUMPERCALL_COL_INDEX = 5
LOCATION_COL_INDEX = 6
NAME_COL_INDEX = 7
CALLERS_COL_INDEX = 8
CALLEES_COL_INDEX = 9


class ProfilingTableItem(QTreeWidgetItem):

    """Profiling table row"""

    def __init__(self, items, isOutside, funcIDs):
        QTreeWidgetItem.__init__(self, items)

        self.__isOutside = isOutside
        self.__funcIDs = funcIDs

        # Set the first column icon
        if isOutside:
            self.setIcon(OUTSIDE_COL_INDEX, getIcon('nonprojectentry.png'))
            self.setToolTip(OUTSIDE_COL_INDEX,
                            'Record of an outside function')
        else:
            self.setIcon(OUTSIDE_COL_INDEX, getIcon('empty.png'))
            self.setToolTip(OUTSIDE_COL_INDEX, '')

        # Set the function name tooltip
        fileName = self.getFileName()
        lineNumber = self.getLineNumber()
        if fileName != "" and lineNumber != 0:
            self.setToolTip(NAME_COL_INDEX,
                            GlobalData().getFileLineDocstring(fileName,
                                                              lineNumber))

        # Sets the location/name columns
        self.updateLocation(False)
        self.setText(NAME_COL_INDEX, self.getFunctionName())

        for column in [CALLS_COL_INDEX, TOTALPERCALL_COL_INDEX,
                       CUM_COL_INDEX, CUMPERCALL_COL_INDEX,
                       CALLERS_COL_INDEX, CALLEES_COL_INDEX]:
            self.setTextAlignment(column, Qt.AlignRight)
        self.setTextAlignment(TOTAL_COL_INDEX, Qt.AlignLeft)

    def isOutside(self):
        """True if it is outside"""
        return self.__isOutside

    def getFuncIDs(self):
        """Provides the function identification exactly as pstats defines it"""
        return self.__funcIDs

    def getFileName(self):
        """Provides the item file name"""
        if self.__funcIDs[0] == '~':
            return ""
        return self.__funcIDs[0]

    def getLineNumber(self):
        """Provides the line number"""
        return self.__funcIDs[1]

    def getFunctionName(self):
        """Provides the function name"""
        name = self.__funcIDs[2]
        if self.__funcIDs[:2] == ('~', 0):
            # special case for built-in functions
            if name.startswith('<') and name.endswith('>'):
                return "{%s}" % name[1:-1]
        return name

    def updateLocation(self, isFull):
        """Updates the function location cell"""
        fileName = self.getFileName()
        if fileName != "":
            if isFull:
                loc = fileName + ":" + str(self.getLineNumber())
            else:
                loc = os.path.basename(fileName) + ":" + \
                      str(self.getLineNumber())
            self.setText(LOCATION_COL_INDEX, loc)
            self.setToolTip(LOCATION_COL_INDEX,
                            fileName + ":" + str(self.getLineNumber()))

    def callersCount(self):
        """Provides the number of callers"""
        return int(str(self.text(CALLERS_COL_INDEX)))

    def calleesCount(self):
        """Provides the number of callees"""
        return int(str(self.text(CALLEES_COL_INDEX)))

    @staticmethod
    def __getActualCalls(txt):
        """Returns the actual number of calls as integer"""
        return int(str(txt).split('/', 1)[0])

    @staticmethod
    def __getFloatValue(txt):
        """Returns a float value from a column"""
        return float(str(txt).split(' ', 1)[0])

    def __lt__(self, other):
        """Integer or string sorting"""
        sortColumn = self.treeWidget().sortColumn()

        if sortColumn == OUTSIDE_COL_INDEX:
            return self.__isOutside < other.__isOutside

        txt = self.text(sortColumn)
        otherTxt = other.text(sortColumn)
        if sortColumn == CALLS_COL_INDEX:
            return self.__getActualCalls(txt) < \
                   self.__getActualCalls(otherTxt)

        if sortColumn in [TOTAL_COL_INDEX, TOTALPERCALL_COL_INDEX,
                          CUM_COL_INDEX, CUMPERCALL_COL_INDEX]:
            return self.__getFloatValue(txt) < \
                   self.__getFloatValue(otherTxt)

        if sortColumn == LOCATION_COL_INDEX:
            sfName = self.getFileName()
            ofName = other.getFileName()
            if sfName == ofName:
                return self.getLineNumber() < other.getLineNumber()
            return sfName < ofName

        if sortColumn == NAME_COL_INDEX:
            return txt < otherTxt

        if sortColumn in [CALLERS_COL_INDEX, CALLEES_COL_INDEX]:
            return int(txt) < int(otherTxt)

        # Fallback to string comparison
        return txt < otherTxt

    def match(self, locationAndName):
        """Checks if the item function location and name
           matches what received
        """
        parts = locationAndName.split(":")
        if len(parts) != 3:
            return False
        return self.getFunctionName() == parts[2] and \
               str(self.getLineNumber()) == parts[1] and \
               self.getFileName() == parts[0]


class ProfilerTreeWidget(QTreeWidget):

    """Need only to generate sigEscapePressed signal"""

    sigEscapePressed = pyqtSignal()

    def __init__(self, parent=None):
        QTreeWidget.__init__(self, parent)

    def keyPressEvent(self, event):
        """Handles the key press events"""
        if event.key() == Qt.Key_Escape:
            self.sigEscapePressed.emit()
            event.accept()
        else:
            QTreeWidget.keyPressEvent(self, event)


class ProfileTableViewer(QWidget):

    """Profiling results table viewer"""

    sigEscapePressed = pyqtSignal()

    def __init__(self, scriptName, params, reportTime,
                 dataFile, stats, parent=None):
        QWidget.__init__(self, parent)

        self.__table = ProfilerTreeWidget(self)
        self.__table.sigEscapePressed.connect(self.__onEsc)

        self.__script = scriptName
        self.__stats = stats
        project = GlobalData().project
        if project.isLoaded():
            self.__projectPrefix = os.path.dirname(project.fileName)
        else:
            self.__projectPrefix = os.path.dirname(scriptName)
        if not self.__projectPrefix.endswith(os.path.sep):
            self.__projectPrefix += os.path.sep

        self.__table.setAlternatingRowColors(True)
        self.__table.setRootIsDecorated(False)
        self.__table.setItemsExpandable(False)
        self.__table.setSortingEnabled(True)
        self.__table.setItemDelegate(NoOutlineHeightDelegate(4))
        self.__table.setUniformRowHeights(True)
        self.__table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.__table.setSelectionBehavior(QAbstractItemView.SelectRows)

        headerLabels = ["", "Calls", "Total time", "Per call",
                        "Cum. time", "Per call", "File name:line",
                        "Function", "Callers", "Callees"]
        self.__table.setHeaderLabels(headerLabels)

        headerItem = self.__table.headerItem()
        headerItem.setToolTip(0, "Indication if it is an outside function")
        headerItem.setToolTip(1, "Actual number of calls/primitive calls "
                              "(not induced via recursion)")
        headerItem.setToolTip(2, "Total time spent in function "
                              "(excluding time made in calls "
                              "to sub-functions)")
        headerItem.setToolTip(3, "Total time divided by number "
                              "of actual calls")
        headerItem.setToolTip(4, "Total time spent in function and all "
                              "subfunctions (from invocation till exit)")
        headerItem.setToolTip(5, "Cumulative time divided by number "
                              "of primitive calls")
        headerItem.setToolTip(6, "Function location")
        headerItem.setToolTip(7, "Function name")
        headerItem.setToolTip(8, "Function callers")
        headerItem.setToolTip(9, "Function callees")

        self.__table.itemActivated.connect(self.__activated)

        totalCalls = self.__stats.total_calls
        # The calls were not induced via recursion
        totalPrimitiveCalls = self.__stats.prim_calls
        totalTime = self.__stats.total_tt

        txt = "<b>Script:</b> " + self.__script + " " + \
              params['arguments'] + "<br/>" \
              "<b>Run at:</b> " + reportTime + "<br/>" + \
              str(totalCalls) + " function calls (" + \
              str(totalPrimitiveCalls) + " primitive calls) in " + \
              FLOAT_FORMAT % totalTime + " CPU seconds"
        summary = QLabel(txt)
        summary.setToolTip(txt)
        summary.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        summary.setStyleSheet('QLabel {' + getLabelStyle(self) + '}')

        vLayout = QVBoxLayout()
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(0)
        vLayout.addWidget(summary)
        vLayout.addWidget(self.__table)

        self.setLayout(vLayout)
        self.__createContextMenu()

        self.__populate(totalTime)

    def __onEsc(self):
        """Triggered when Esc is pressed"""
        self.sigEscapePressed.emit()

    def __createContextMenu(self):
        """Creates context menu for the table raws"""
        self.__contextMenu = QMenu(self)
        self.__callersMenu = QMenu("Callers", self)
        self.__outsideCallersMenu = QMenu("Outside callers", self)
        self.__calleesMenu = QMenu("Callees", self)
        self.__outsideCalleesMenu = QMenu("Outside callees", self)
        self.__contextMenu.addMenu(self.__callersMenu)
        self.__contextMenu.addMenu(self.__outsideCallersMenu)
        self.__contextMenu.addSeparator()
        self.__contextMenu.addMenu(self.__calleesMenu)
        self.__contextMenu.addMenu(self.__outsideCalleesMenu)

        self.__callersMenu.triggered.connect(self.__onCallContextMenu)
        self.__outsideCallersMenu.triggered.connect(self.__onCallContextMenu)
        self.__calleesMenu.triggered.connect(self.__onCallContextMenu)
        self.__outsideCalleesMenu.triggered.connect(self.__onCallContextMenu)

        self.__table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.__table.customContextMenuRequested.connect(self.__showContextMenu)

    def __showContextMenu(self, point):
        """Context menu"""
        self.__callersMenu.clear()
        self.__outsideCallersMenu.clear()
        self.__calleesMenu.clear()
        self.__outsideCalleesMenu.clear()

        # Detect what the item was clicked
        item = self.__table.itemAt(point)
        funcName = item.getFunctionName()

        # Build the context menu
        if item.callersCount() == 0:
            self.__callersMenu.setEnabled(False)
            self.__outsideCallersMenu.setEnabled(False)
        else:
            callers = self.__stats.stats[item.getFuncIDs()][4]
            callersList = list(callers.keys())
            callersList.sort()
            for callerFunc in callersList:
                menuText = self.__getCallLine(callerFunc, callers[callerFunc])
                if self.__isOutsideItem(callerFunc[0]):
                    act = self.__outsideCallersMenu.addAction(menuText)
                else:
                    act = self.__callersMenu.addAction(menuText)
                funcFileName, funcLine, funcName = \
                    self.__getLocationAndName(callerFunc)
                act.setData(funcFileName + ":" + str(funcLine) +
                            ":" + funcName)
            self.__callersMenu.setEnabled(not self.__callersMenu.isEmpty())
            self.__outsideCallersMenu.setEnabled(
                not self.__outsideCallersMenu.isEmpty())

        if item.calleesCount() == 0:
            self.__calleesMenu.setEnabled(False)
            self.__outsideCalleesMenu.setEnabled(False)
        else:
            callees = self.__stats.all_callees[item.getFuncIDs()]
            calleesList = list(callees.keys())
            calleesList.sort()
            for calleeFunc in calleesList:
                menuText = self.__getCallLine(calleeFunc, callees[calleeFunc])
                if self.__isOutsideItem(calleeFunc[0]):
                    act = self.__outsideCalleesMenu.addAction(menuText)
                else:
                    act = self.__calleesMenu.addAction(menuText)
                funcFileName, funcLine, funcName = \
                    self.__getLocationAndName(calleeFunc)
                act.setData(funcFileName + ":" +
                            str(funcLine) + ":" + funcName)
            self.__calleesMenu.setEnabled(not self.__calleesMenu.isEmpty())
            self.__outsideCalleesMenu.setEnabled(
                not self.__outsideCalleesMenu.isEmpty())

        self.__contextMenu.popup(QCursor.pos())

    def __resize(self):
        """Resizes columns to the content"""
        self.__table.header().resizeSections(QHeaderView.ResizeToContents)
        self.__table.header().setStretchLastSection(True)
        self.__table.header().resizeSection(OUTSIDE_COL_INDEX, 28)
        self.__table.header().setSectionResizeMode(OUTSIDE_COL_INDEX,
                                                   QHeaderView.Fixed)

    def setFocus(self):
        """Set focus to the proper widget"""
        self.__table.setFocus()

    def __isOutsideItem(self, fileName):
        """Detects if the record should be shown as an outside one"""
        return not fileName.startswith(self.__projectPrefix)

    def __activated(self, item, column):
        """Triggered when the item is activated"""
        try:
            line = item.getLineNumber()
            fileName = item.getFileName()
            if line == 0 or not os.path.isabs(fileName):
                return
            GlobalData().mainWindow.openFile(fileName, line)
        except:
            logging.error("Could not jump to function location")

    @staticmethod
    def __getFuncShortLocation(funcFileName, funcLine):
        """Provides unified shortened function location"""
        if funcFileName == "":
            return ""
        return os.path.basename(funcFileName) + ":" + str(funcLine)

    def __getCallLine(self, func, props):
        """Provides the formatted call line"""
        funcFileName, funcLine, funcName = self.__getLocationAndName(func)
        if isinstance(props, tuple):
            actualCalls, primitiveCalls, totalTime, cumulativeTime = props
            if primitiveCalls != actualCalls:
                callsString = str(actualCalls) + "/" + str(primitiveCalls)
            else:
                callsString = str(actualCalls)

            return callsString + "\t" + FLOAT_FORMAT % totalTime + "\t" + \
                   FLOAT_FORMAT % cumulativeTime + "\t" + \
                   self.__getFuncShortLocation(funcFileName, funcLine) + \
                   "(" + funcName + ")"

        # I've never seen this branch working so it is just in case.
        # There was something like this in the pstats module
        return self.__getFuncShortLocation(funcFileName, funcLine) + \
               "(" + funcName + ")"

    @staticmethod
    def __getLocationAndName(func):
        """Provides standardized function file name, line and its name"""
        if func[:2] == ('~', 0):
            # special case for built-in functions
            name = func[2]
            if name.startswith('<') and name.endswith('>'):
                return "", 0, "{%s}" % name[1:-1]
            return "", 0, name
        return func[0], func[1], func[2]

    def __createItem(self, func, totalCPUTime,
                     primitiveCalls, actualCalls, totalTime,
                     cumulativeTime, timePerCall, cumulativeTimePerCall,
                     callers):
        """Creates an item to display"""
        values = []
        values.append("")
        if primitiveCalls == actualCalls:
            values.append(str(actualCalls))
        else:
            values.append(str(actualCalls) + "/" + str(primitiveCalls))

        if totalCPUTime == 0.0:
            values.append(FLOAT_FORMAT % totalTime)
        else:
            values.append(FLOAT_FORMAT % totalTime +
                          " \t(%3.2f%%)" % (totalTime / totalCPUTime * 100))
        values.append(FLOAT_FORMAT % timePerCall)
        values.append(FLOAT_FORMAT % cumulativeTime)
        values.append(FLOAT_FORMAT % cumulativeTimePerCall)

        # Location and name will be filled in the item constructor
        values.append("")
        values.append("")

        # Callers
        callersCount = len(callers)
        values.append(str(callersCount))

        # Callees
        if func in self.__stats.all_callees:
            calleesCount = len(self.__stats.all_callees[func])
        else:
            calleesCount = 0
        values.append(str(calleesCount))

        item = ProfilingTableItem(values, self.__isOutsideItem(func[0]), func)

        if callersCount != 0:
            tooltip = ""
            callersList = list(callers.keys())
            callersList.sort()
            for callerFunc in callersList[:MAX_CALLS_IN_TOOLTIP]:
                if tooltip != "":
                    tooltip += "\n"
                tooltip += self.__getCallLine(callerFunc, callers[callerFunc])
            if callersCount > MAX_CALLS_IN_TOOLTIP:
                tooltip += "\n. . ."
            item.setToolTip(8, tooltip)

        if calleesCount != 0:
            callees = self.__stats.all_callees[func]
            tooltip = ""
            calleesList = list(callees.keys())
            calleesList.sort()
            for calleeFunc in calleesList[:MAX_CALLS_IN_TOOLTIP]:
                if tooltip != "":
                    tooltip += "\n"
                tooltip += self.__getCallLine(calleeFunc, callees[calleeFunc])
            if calleesCount > MAX_CALLS_IN_TOOLTIP:
                tooltip += "\n. . ."
            item.setToolTip(9, tooltip)

        self.__table.addTopLevelItem(item)

    def __populate(self, totalCPUTime):
        """Populates the data"""
        for func, (primitiveCalls, actualCalls, totalTime,
                   cumulativeTime, callers) in self.__stats.stats.items():
            # Calc time per call
            if actualCalls == 0:
                timePerCall = 0.0
            else:
                timePerCall = totalTime / actualCalls

            # Calc time per cummulative call
            if primitiveCalls == 0:
                cumulativeTimePerCall = 0.0
            else:
                cumulativeTimePerCall = cumulativeTime / primitiveCalls

            self.__createItem(func, totalCPUTime,
                              primitiveCalls, actualCalls, totalTime,
                              cumulativeTime, timePerCall,
                              cumulativeTimePerCall, callers)
        self.__resize()
        self.__table.header().setSortIndicator(2, Qt.DescendingOrder)
        self.__table.sortItems(2, self.__table.header().sortIndicatorOrder())

    def togglePath(self, state):
        """Switches between showing full paths or file names in locations"""
        for index in range(0, self.__table.topLevelItemCount()):
            self.__table.topLevelItem(index).updateLocation(state)
        self.__resize()
        return

    def __onCallContextMenu(self, act):
        """Triggered when a context menu action is requested"""
        name = str(act.data().toString())
        for index in range(0, self.__table.topLevelItemCount()):
            item = self.__table.topLevelItem(index)
            if item.match(name):
                self.__table.clearSelection()
                self.__table.scrollToItem(item)
                self.__table.setCurrentItem(item)

    def onSaveAs(self, fileName):
        """Saves the table to a file in CSV format"""
        try:
            f = open(fileName, "wt")
            headerItem = self.__table.headerItem()
            outsideIndex = -1
            for index in range(0, headerItem.columnCount()):
                title = str(headerItem.text(index))
                if title == "":
                    outsideIndex = index
                    title = "Outside"
                if index != 0:
                    f.write(',' + title)
                else:
                    f.write(title)

            for index in range(0, self.__table.topLevelItemCount()):
                item = self.__table.topLevelItem(index)
                f.write("\n")
                for column in range(0, item.columnCount()):
                    if column != 0:
                        f.write(',')
                    if column == outsideIndex:
                        if item.isOutside():
                            f.write("Y")
                        else:
                            f.write("N")
                    else:
                        text = str(item.text(column))
                        f.write(text.replace('\t', ''))
            f.close()
        except Exception as ex:
            logging.error(ex)
