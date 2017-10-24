# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2011-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# The implementation vastly derived from eric4. Here is the original copyright:
# Copyright (c) 2002 - 2013 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""Debugger variable browser items"""

from ui.qt import Qt, QTreeWidgetItem
from utils.pixmapcache import getIcon

INDICATORS = ("()", "[]", "{:}", "{}")


def getDisplayValue(displayValue):
    """Takes potentially multilined value and converts it to a single line"""
    lines = str(displayValue).splitlines()
    lineCount = len(lines)
    if lineCount > 1:
        # There are many lines. Find first non-empty.
        nonEmptyIndex = None
        index = -1
        for line in lines:
            index += 1
            if len(line.strip()) > 0:
                nonEmptyIndex = index
                break
        if nonEmptyIndex is None:
            displayValue = ""   # Multilined empty string
        else:
            if len(lines[nonEmptyIndex]) > 128:
                displayValue = lines[nonEmptyIndex][:128] + "<...>"
            else:
                displayValue = lines[nonEmptyIndex]
                if nonEmptyIndex < lineCount - 1:
                    displayValue += "<...>"

            if nonEmptyIndex > 0:
                displayValue = "<...>" + displayValue
    elif lineCount == 1:
        # There is just one line
        if len(lines[0]) > 128:
            displayValue = lines[0][:128] + "<...>"
        else:
            value = lines[0]
    return displayValue


def getTooltipValue(value):
    """Takes a potentially multilined string and converts it to
       the form suitable for tooltips
    """
    lines = value.splitlines()
    lineCount = len(lines)
    if lineCount > 1:
        value = ""
        index = 0
        for line in lines:
            if index >= 5:  # First 5 lines only
                break
            if index > 0:
                value += "\n"
            if len(line) > 128:
                value += line[:128] + "<...>"
            else:
                value += line
            index += 1
        if lineCount > 5:
            value += "\n<...>"
    elif lineCount == 1:
        if len(lines[0]) > 128:
            value = lines[0][:128] + "<...>"
        else:
            value = lines[0]
    return value


class VariableItem(QTreeWidgetItem):

    """Base structure for variable items"""

    def __init__(self, parent, isGlobal,
                 displayName, displayValue, displayType):
        self.__isGlobal = isGlobal
        self.__value = displayValue
        self.__type = displayType

        self.__name, self.__varID = VariableItem.extractId(displayName)

        # Decide about the display value
        displayValue = getDisplayValue(displayValue)

        # Decide about the tooltip
        self.__tooltip = "Name: " + self.__name + "\n" + \
                         "Type: " + displayType + "\n" + \
                         "Value: "

        tooltipDisplayValue = getTooltipValue(self.__value)
        if '\r' in tooltipDisplayValue or '\n' in tooltipDisplayValue:
            self.__tooltip += "\n" + tooltipDisplayValue
        else:
            self.__tooltip += tooltipDisplayValue

        QTreeWidgetItem.__init__(self, parent, [self.__name, displayValue,
                                                displayType])
        self.populated = True

    def getValue(self):
        """Provides the variable value"""
        return self.__value

    def getId(self):
        """Provides the variable ID"""
        return self.__varID

    def getName(self):
        """Provides the variable name"""
        return self.__name

    def getType(self):
        """Provides the variable type"""
        return self.__type

    def isGlobal(self):
        """Tells if the variable is global"""
        return self.__isGlobal

    @classmethod
    def extractId(cls, var):
        """Extracts the variable ID"""
        if " (ID:" in var:
            dvar, varID = var.rsplit(None, 1)
            if varID.endswith(INDICATORS):
                varID, indicators = VariableItem.extractIndicators(varID)
                dvar += indicators
        else:
            dvar = var
            varID = None
        return dvar, varID

    @classmethod
    def extractIndicators(cls, var):
        """Extract the indicator string from a variable text"""
        for indicator in INDICATORS:
            if var.endswith(indicator):
                return var[:-len(indicator)], indicator
        return var, ""

    def _buildKey(self):
        """Builds a key to access to the variable"""
        indicators = ""
        txt = self.text(0)
        if txt.endswith(INDICATORS):
            txt, indicators = VariableItem.extractIndicators(txt)
        if self.__varID:
            txt = "{0} {1}{2}".format(txt, self.__varID, indicators)
        else:
            txt = "{0}{1}".format(txt, indicators)
        return txt

    def data(self, column, role):
        """Provides the data for the requested role"""
        if role == Qt.ToolTipRole:
            return self.__tooltip
        if role == Qt.DecorationRole:
            if column == 0:
                if not self.parent():
                    if self.__isGlobal:
                        fileName = 'globvar.png'
                    else:
                        fileName = 'locvar.png'
                    return getIcon(fileName)
        return QTreeWidgetItem.data(self, column, role)

    def attachDummy(self):
        """Attach a dummy sub item to allow for lazy population"""
        QTreeWidgetItem(self, ["DUMMY"])

    def deleteChildren(self):
        """Deletes all children (cleaning the subtree)"""
        for item in self.takeChildren():
            del item

    def expand(self):
        """Does nothing for the basic item. Should be overwritten"""
        pass

    def collapse(self):
        """Does nothing for the basic item. Should be overwritten"""
        pass



class SpecialVariableItem(VariableItem):

    """These special variable nodes are generated for classes, lists,
       tuples and dictionaries.
    """

    def __init__(self, parent, debugger, isGlobal,
                 displayName, displayValue, displayType, frameNumber):
        VariableItem.__init__(self, parent, isGlobal,
                              displayName, displayValue, displayType)
        self.attachDummy()
        self.populated = False

        self.frameNumber = frameNumber
        self.__debugger = debugger

    def expand(self):
        """Expands the item"""
        self.deleteChildren()
        self.populated = True

        pathlist = [self._buildKey()]
        par = self.parent()

        # Step 1: get a pathlist up to the requested variable
        while par is not None:
            pathlist.insert(0, par._buildKey())
            par = par.parent()

        # Step 2: request the variable from the debugger
        self.__debugger.remoteClientVariable(self.isGlobal(),
                                             pathlist, self.frameNumber)


class ArrayElementVariableItem(VariableItem):

    """Represents an array element"""

    def __init__(self, parent, isGlobal,
                 displayName, displayValue, displayType):
        VariableItem.__init__(self, parent, isGlobal,
                              displayName, displayValue, displayType)

        """
        Array elements have numbers as names, but the key must be
        right justified and zero filled to 6 decimal places. Then
        element 2 will have a key of '000002' and appear before
        element 10 with a key of '000010'
        """
        col0Str = self.text(0)
        self.setText(0, "{0:6d}".format(int(col0Str)))


class SpecialArrayElementVariableItem(SpecialVariableItem):

    """Represents a special array variable node"""

    def __init__(self, parent, debugger, isGlobal,
                 displayName, displayValue, displayType, frameNumber):
        SpecialVariableItem.__init__(self, parent, debugger, isGlobal,
                                     displayName, displayValue, displayType,
                                     frameNumber)
        """
        Array elements have numbers as names, but the key must be
        right justified and zero filled to 6 decimal places. Then
        element 2 will have a key of '000002' and appear before
        element 10 with a key of '000010'
        """
        col0Str, indicators = VariableItem.extractIndicators(self.text(0))
        self.setText(0, "{0:6d}{1}".format(int(col0Str), indicators))
