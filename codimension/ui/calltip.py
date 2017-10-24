# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy sergey.satskiy@gmail.com
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

"""Custom calltips"""


from utils.globals import GlobalData
from .qt import (Qt, QEventLoop, QSizePolicy, QFrame, QLabel, QApplication,
                 QGridLayout)


class Calltip(QFrame):

    """Frameless panel with a calltip"""

    def __init__(self, parent):
        QFrame.__init__(self, parent)

        # Make the frame nice looking
        palette = self.palette()
        palette.setColor(self.backgroundRole(),
                         GlobalData().skin['calltipPaper'])
        self.setPalette(palette)

        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(2)
        self.setAutoFillBackground(True)

        # Keep pylint happy
        self.__calltipLabel = None
        self.__text = None
        self.__paramPositions = None
        self.__highlightedParam = None

        self.__createLayout()
        QFrame.hide(self)
        self.setFocusPolicy(Qt.NoFocus)

    def __createLayout(self):
        """Creates the widget layout"""
        self.__calltipLabel = QLabel('')
        self.__calltipLabel.setSizePolicy(QSizePolicy.Ignored,
                                          QSizePolicy.Fixed)
        self.__calltipLabel.setWordWrap(False)
        self.__calltipLabel.setAlignment(Qt.AlignLeft)
        palette = self.__calltipLabel.palette()
        palette.setColor(self.foregroundRole(),
                         GlobalData().skin['calltipColor'])
        self.__calltipLabel.setPalette(palette)

        gridLayout = QGridLayout(self)
        gridLayout.setContentsMargins(3, 3, 3, 3)
        gridLayout.addWidget(self.__calltipLabel, 0, 0, 1, 1)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def resize(self):
        """Resizes the dialogue to match the editor size"""
        vscroll = self.parent().verticalScrollBar()
        if vscroll.isVisible():
            scrollWidth = vscroll.width()
        else:
            scrollWidth = 0

        hscroll = self.parent().horizontalScrollBar()
        if hscroll.isVisible():
            scrollHeight = hscroll.height()
        else:
            scrollHeight = 0

        # Panel
        width = self.parent().width()
        height = self.parent().height()
        widgetWidth = width - scrollWidth - 6 - 1

        self.setFixedWidth(widgetWidth)

        vPos = height - self.height() - scrollHeight
        self.move(3, vPos - 3)

    def showCalltip(self, message, paramNumber):
        """Brings up the panel with the required text"""
        self.__text = message
        self.__calcParamPositions()
        self.highlightParameter(paramNumber)
        QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)

        self.resize()
        self.show()

        # I have to do resize() twice because the self.height() value is
        # calculated in a different way before the frame is shown and after.
        # So the first call moves the widget to the nearly right location
        # and the second to the precise one
        self.resize()

    def highlightParameter(self, number):
        """Hightlights the given parameter number, 0 - based"""
        if number == self.__highlightedParam:
            return
        if self.__paramPositions is None:
            self.__calltipLabel.setText(self.__text)
            return
        if number >= len(self.__paramPositions):
            self.__calltipLabel.setText(self.__text)
            return
        positions = self.__paramPositions[number]
        highlight = self.__text[0:positions[0]] + "<font color='" + \
                    GlobalData().skin['calltipHighColor'].name() + "'>" + \
                    self.__text[positions[0]:positions[1] + 1] + \
                    "</font>" + self.__text[positions[1] + 1:]
        self.__calltipLabel.setText(highlight)

    def __calcParamPositions(self):
        """Calculates the parameter positions in the calltip text"""
        if self.__text is None or '\n' in self.__text:
            self.__paramPositions = None
            return

        try:
            begin = self.__text.index('(') + 1
        except:
            self.__paramPositions = None
            return

        if self.__text[begin] == '.':
            # Special case for f(...)
            self.__paramPositions = None
            return

        self.__paramPositions = []
        lastIndex = len(self.__text) - 1
        index = begin
        level = 0               # Unconditional skip of commas
        singleQuote = False
        doubleQuote = False
        while index <= lastIndex:
            ch = self.__text[index]
            if ch == "'" and singleQuote:
                singleQuote = False
            elif ch == '"' and doubleQuote:
                doubleQuote = False
            elif ch == "'":
                singleQuote = False
            elif ch == '"':
                doubleQuote = False
            elif ch in ['(', '{']:
                level += 1
            elif ch in [')', '}']:
                level -= 1
                if level == -1:
                    # Closing bracket
                    if index > begin:
                        self.__paramPositions.append((begin, index - 1))
                    break
            elif ch == '[':
                if level > 0:
                    index += 1
                    continue
                # if a previous char is '=' then it is a default paam
                checkIndex = index - 1
                while self.__text[checkIndex].isspace():
                    checkIndex -= 1
                if self.__text[checkIndex] == '=':
                    level += 1
                    index += 1
                    continue

                if self.__text[checkIndex] == '(':
                    # The very first round bracket
                    index = index + 1
                    begin = index
                    continue

                # '[' after a parameter name
                if index > begin:
                    self.__paramPositions.append((begin, index - 1))
                    # The next meaningfull character is comma or an identifier
                    index += 1
                    while index <= lastIndex and self.__text[index].isspace():
                        index += 1
                    if self.__text[index] == ',':
                        index += 1
                    index += 1
                    begin = index
                    continue

                # I don't know what it is
                self.__paramPositions = None
                return

            elif ch == ']':
                if level > 0:
                    level -= 1
                    index += 1
                    continue

                # This must be an optional argument closing bracket
                checkIndex = index - 1
                while self.__text[checkIndex].isspace():
                    checkIndex -= 1

                if self.__text[checkIndex] == ']':
                    index += 1
                    continue

                # Need to add and this is the last parameter
                if index > begin:
                    self.__paramPositions.append((begin, index - 1))
                break

            elif ch == ',':
                if level == 0:
                    self.__paramPositions.append((begin, index - 1))
                # Skip till the beginning of the next
                # parameter - it must be there
                index += 1
                while index <= lastIndex and self.__text[index].isspace():
                    index += 1
                begin = index
                continue

            index += 1

        if len(self.__paramPositions) == 0:
            self.__paramPositions = None

    def hide(self):
        """Handles the hiding of the panel and markers"""
        QFrame.hide(self)
        self.__text = None
        self.__paramPositions = None
        self.__highlightedParam = None
        self.__calltipLabel.setText("")
