# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2020  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Search support"""


from os.path import isabs, exists
import re
import logging
from html import escape
from utils.globals import GlobalData
from utils.fileutils import isPythonFile, getFileContent
from cdmpyparser import getBriefModuleInfoFromMemory


class Match:

    """Stores info about one match in a file"""

    def __init__(self, line, start, finish):
        self.line = line        # Matched line
        self.start = start      # Match start pos
        self.finish = finish    # Match end pos
        self.tooltip = "not implemented"
        self.text = ""


def getSearchItemIndex(items, fileName):
    """Provides the search item index basing on the file name"""
    index = 0
    for item in items:
        if item.fileName == fileName:
            return index
        index += 1
    return -1


class ItemToSearchIn:

    """Stores information about one item to search in"""

    contextLines = 15

    def __init__(self, fname, bufferID):
        self.fileName = fname       # Could be absolute -> for existing files
                                    # or relative -> for newly created
        self.bufferUUID = bufferID  # Non empty for currently opened files
        self.tooltip = ""           # For python files only -> docstring
        self.matches = []

    def addMatch(self, name, lineNumber, customMessage=None):
        """Used to add a match which was found outside of find in files"""
        match = Match(lineNumber, 0, 0)

        # Load the file and identify matched line and tooltip
        try:
            if self.bufferUUID != "":
                mainWindow = GlobalData().mainWindow
                widget = mainWindow.getWidgetByUUID(self.bufferUUID)
                if widget is not None:
                    content = widget.getEditor().lines
                else:
                    raise Exception('Inconsistency. Buffer disappeared.')
            else:
                content = getFileContent(self.fileName).splitlines()
            self.__fillInMatch(match, content, name, lineNumber, customMessage)
        except Exception as exc:
            logging.error('Error adding match: %s', str(exc))
        self.matches.append(match)

    def __fillInMatch(self, match, content, name, lineNumber,
                      customMessage=None):
        """Fills in the match fields from the content"""
        # Form the regexp corresponding to a single word search
        line = content[lineNumber - 1]
        if customMessage:
            match.text = customMessage
        else:
            match.text = line.strip()

        if name:
            regexpText = re.escape(name)
            regexpText = "\\b%s\\b" % regexpText
            flags = re.UNICODE
            searchRegexp = re.compile(regexpText, flags)

            contains = searchRegexp.search(line)
            match.start = contains.start()
            match.finish = contains.end()
        else:
            match.start = 0
            match.finish = len(line)

        match.tooltip = self.__buildTooltip(content, lineNumber - 1,
                                            len(content),
                                            match.start, match.finish)

        self.__extractDocstring(content)

    def search(self, expression):
        """Perform search within this item"""
        self.matches = []
        if self.bufferUUID != "":
            # Search item is the currently loaded buffer
            mainWindow = GlobalData().mainWindow
            widget = mainWindow.getWidgetByUUID(self.bufferUUID)
            if widget is not None:
                # Search in the buffer

                self.__lookThroughLines(widget.getEditor().lines, expression)
                return

        # Here: there were no buffer or have not found it
        #       try searching in a file
        if not isabs(self.fileName) or not exists(self.fileName):
            # Unfortunately not all network file systems report the
            # fact that a file has been deleted from the disk so
            # let's simply ignore such files
            return

        # File exists, search in the file
        try:
            content = getFileContent(self.fileName).splitlines()
            self.__lookThroughLines(content, expression)
        except Exception as exc:
            logging.error('Error searching in %s: %s', self.fileName, str(exc))

    def __buildTooltip(self, content, lineIndex, totalLines,
                       startPos, finishPos):
        """Forms the tooltip for the given match"""
        start, end = self.__calculateContextStart(lineIndex, totalLines)
        lines = content[start:end]
        matchIndex = lineIndex - start

        # Avoid incorrect tooltips for HTML/XML files
        for index in range(0, len(lines)):
            if index != matchIndex:
                lines[index] = escape(lines[index])

        lines[matchIndex] = \
            escape(lines[matchIndex][:startPos]) + \
            "<b>" + \
            escape(lines[matchIndex][startPos:finishPos]) + \
            "</b>" + \
            escape(lines[matchIndex][finishPos:])

        # Strip empty lines at the end and at the beginning
        index = len(lines) - 1
        while index >= 0:
            if lines[index].strip() == '':
                del lines[index]
                index -= 1
                continue
            break
        while len(lines) > 0:
            if lines[0].strip() == '':
                del lines[0]
                continue
            break

        return '<p>' + '<br/>'.join(lines).replace(' ', '&nbsp;') + '</p>'

    def __lookThroughLines(self, content, expression):
        """Searches through all the given lines"""
        lineIndex = 0
        totalLines = len(content)
        while lineIndex < totalLines:
            line = content[lineIndex]
            contains = expression.search(line)
            if contains:
                match = Match(lineIndex + 1, contains.start(), contains.end())
                match.text = line.strip()
                match.tooltip = self.__buildTooltip(content, lineIndex,
                                                    totalLines,
                                                    match.start, match.finish)
                self.matches.append(match)
                if len(self.matches) > 1024:
                    # Too much entries, stop here
                    logging.warning("More than 1024 matches in %s. Stop "
                                    "further search in this file.",
                                    self.fileName)
                    break
            lineIndex += 1

        # Extract docsting if applicable
        if len(self.matches) > 0:
            self.__extractDocstring(content)

    def __extractDocstring(self, content):
        """Extracts a docstring and sets it as a tooltip if needed"""
        if self.tooltip != "":
            return

        if isPythonFile(self.fileName):
            info = getBriefModuleInfoFromMemory("\n".join(content))
            self.tooltip = ""
            if info.docstring is not None:
                self.tooltip = info.docstring.text

    @staticmethod
    def __calculateContextStart(matchedLine, totalLines):
        """Calculates the start line number for the context tooltip"""
        # matchedLine is a zero based index
        if ItemToSearchIn.contextLines >= totalLines:
            return 0, totalLines

        start = matchedLine - int(ItemToSearchIn.contextLines / 2)
        if start < 0:
            start = 0
        end = start + ItemToSearchIn.contextLines
        if end < totalLines:
            return start, end
        return totalLines - ItemToSearchIn.contextLines, totalLines

