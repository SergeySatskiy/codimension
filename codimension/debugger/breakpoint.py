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

"""Debugger breakpoint"""

import os, os.path
from utils.globals import GlobalData


class Breakpoint:

    """Represents a single breakpoint"""

    def __init__(self, fileName=None, lineNumber=None, condition="",
                 temporary=False, enabled=True, ignoreCount=0):
        if fileName is None:
            self.__fileName = fileName
        elif os.path.isabs(fileName):
            project = GlobalData().project
            if project.isLoaded():
                if project.isProjectFile(fileName):
                    # This is a project file; strip the project dir
                    self.__fileName = fileName.replace(
                        project.getProjectDir(), "")
                else:
                    # Not a project file, save as is
                    self.__fileName = fileName
            else:
                # Pretty much impossible
                self.__fileName = fileName
        else:
            # Relative path, i.e. a project file
            self.__fileName = fileName

        self.__lineNumber = lineNumber
        self.__condition = condition
        self.__temporary = temporary
        self.__enabled = enabled
        self.__ignoreCount = ignoreCount

    def update(self, otherBreakPoint):
        """Basically copies values from another breakpoint"""
        self.__fileName = otherBreakPoint.getFileName()
        self.__lineNumber = otherBreakPoint.getLineNumber()
        self.__condition = otherBreakPoint.getCondition()
        self.__temporary = otherBreakPoint.isTemporary()
        self.__enabled = otherBreakPoint.isEnabled()
        self.__ignoreCount = otherBreakPoint.getIgnoreCount()

    def updateLineNumber(self, line):
        """Updates the line #. Used when there are changes in the editor"""
        self.__lineNumber = line

    def isValid(self):
        """True if the breakpoint is valid"""
        if self.__fileName is None:
            return False

        if os.path.isabs(self.__fileName):
            if not os.path.exists(self.__fileName):
                return False
        else:
            project = GlobalData().project
            if project.isLoaded():
                path = project.getProjectDir() + self.__fileName
                if not os.path.exists(path):
                    return False
            else:
                if not os.path.exists(self.__fileName):
                    return False

        return self.__lineNumber is not None and self.__lineNumber > 0

    def getFileName(self):
        """Provides the file name"""
        return self.__fileName

    def getAbsoluteFileName(self):
        """Provides the absolute file name"""
        if self.__fileName is None:
            return None
        if os.path.isabs(self.__fileName):
            return self.__fileName

        project = GlobalData().project
        if project.isLoaded():
            return project.getProjectDir() + self.__fileName
        return os.path.abspath(self.__fileName)

    def getLineNumber(self):
        """Provides the line number"""
        return self.__lineNumber

    def getCondition(self):
        """Provides the condition"""
        return self.__condition

    def isTemporary(self):
        """True if temporary"""
        return self.__temporary

    def setTemporary(self, temp):
        """Sets the new value"""
        self.__temporary = temp

    def isEnabled(self):
        """True if enabled"""
        return self.__enabled

    def setEnabled(self, enabled):
        """Sets the new value"""
        self.__enabled = enabled

    def getIgnoreCount(self):
        """Provides the ignore count"""
        return self.__ignoreCount

    def getLocation(self, fullForm=False):
        """Provides the breakpoint location"""
        if self.__fileName is None:
            return str(self.__fileName) + ":" + str(self.__lineNumber)

        if fullForm:
            return self.getAbsoluteFileName() + ":" + str(self.__lineNumber)

        return os.path.basename(self.__fileName) + ":" + str(self.__lineNumber)

    def getTooltip(self):
        """Provides the breakpoint tooltip"""
        return "Location: " + self.getLocation(True) + "\n" \
               "Enabled: " + str(self.__enabled) + "\n" \
               "Temporary: " + str(self.__temporary) + "\n" \
               "Ignore count: " + str(self.__ignoreCount) + "\n" \
               "Condition: " + self.__condition

    def serialize(self):
        """Serializes the breakpoint to a string"""
        return {'file': self.__fileName,
                'line': self.__lineNumber,
                'condition': self.__condition,
                'temp': self.__temporary,
                'enabled': self.__enabled,
                'ignorecnt': self.__ignoreCount}

    def deserialize(self, source):
        """Deserializes the breakpoint"""
        self.__fileName = source.get('file', None)
        self.__lineNumber = source.get('line', None)
        self.__condition = source.get('condition', None)
        self.__temporary = source.get('temp', False)
        self.__enabled = source.get('enabled', False)
        self.__ignoreCount = source.get('ignorecnt', 0)
        return self.isValid()

    def __eq__(self, other):
        """True if equal"""
        return self.__fileName == other.__fileName and \
               self.__lineNumber == other.__lineNumber and \
               self.__condition == other.__condition and \
               self.__temporary == other.__temporary and \
               self.__enabled == other.__enabled and \
               self.__ignoreCount == other.__ignoreCount
