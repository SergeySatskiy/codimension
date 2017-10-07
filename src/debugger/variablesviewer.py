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

"""Variables viewer"""


from ui.qt import (Qt, QFrame, QVBoxLayout, QLabel, QWidget, QSizePolicy,
                   QSpacerItem, QGridLayout, QHBoxLayout, QToolButton,
                   QPushButton, QMenu)
from ui.combobox import CDMComboBox
from utils.pixmapcache import getIcon
from utils.settings import Settings
from utils.colorfont import getLabelStyle, HEADER_HEIGHT, HEADER_BUTTON
from utils.globals import GlobalData
from .variablesbrowser import VariablesBrowser
from .varfilters import VARIABLE_FILTERS


class VariablesViewer(QWidget):

    """Implements the variables viewer for a debugger"""

    # First group of filters
    FilterGlobalAndLocal = 0
    FilterGlobalOnly = 1
    FilterLocalOnly = 2

    def __init__(self, debugger, parent=None):
        QWidget.__init__(self, parent)

        self.__debugger = debugger
        self.__browser = VariablesBrowser(debugger, self)
        self.__createLayout()

        self.setTabOrder(self.__browser, self.__execStatement)
        self.setTabOrder(self.__execStatement, self.__execButton)

        self.__updateFilter()

    def __createLayout(self):
        """Creates the widget layout"""
        verticalLayout = QVBoxLayout(self)
        verticalLayout.setContentsMargins(0, 0, 0, 0)
        verticalLayout.setSpacing(0)

        headerFrame = QFrame()
        headerFrame.setObjectName('varsheader')
        headerFrame.setStyleSheet('QFrame#varsheader {' +
                                  getLabelStyle(self) + '}')
        headerFrame.setFixedHeight(HEADER_HEIGHT)

        self.__headerLabel = QLabel("Variables")

        expandingSpacer = QSpacerItem(10, 10, QSizePolicy.Expanding)

        self.__filterMenu = QMenu(self)
        self.__showAllAct =  self.__filterMenu.addAction('Show all variables')
        self.__showAllAct.setData('showall')
        self.__filterMenu.addSeparator()
        self.__filters = []
        for title, settingName, _ in VARIABLE_FILTERS:
            action = self.__filterMenu.addAction(title)
            action.setCheckable(True)
            action.setData(settingName)
            self.__filters.append(action)
        self.__filterMenu.aboutToShow.connect(self.__filterMenuAboutToShow)
        self.__filterMenu.triggered.connect(self.__filterMenuTriggered)

        self.__filterButton = QToolButton(self)
        self.__filterButton.setIcon(getIcon('dbgvarflt.png'))
        self.__filterButton.setToolTip('Variable filter')
        self.__filterButton.setPopupMode(QToolButton.InstantPopup)
        self.__filterButton.setMenu(self.__filterMenu)
        self.__filterButton.setFocusPolicy(Qt.NoFocus)
        self.__filterButton.setFixedSize(HEADER_BUTTON, HEADER_BUTTON)

        self.__execStatement = CDMComboBox(True)
        self.__execStatement.setSizePolicy(QSizePolicy.Expanding,
                                           QSizePolicy.Expanding)
        self.__execStatement.lineEdit().setToolTip(
            "Execute statement")
        self.__execStatement.setFixedHeight(26)
        self.__execStatement.editTextChanged.connect(
            self.__execStatementChanged)
        self.__execStatement.enterClicked.connect(self.__onEnterInExec)
        self.__execButton = QPushButton("Exec")
        self.__execButton.setEnabled(False)
        self.__execButton.setFixedHeight(26)
        self.__execButton.clicked.connect(self.__onExec)

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins(0, 0, 0, 0)
        headerLayout.setSpacing(0)
        headerLayout.addSpacing(3)
        headerLayout.addWidget(self.__headerLabel)
        headerLayout.addSpacerItem(expandingSpacer)
        headerLayout.addWidget(self.__filterButton)
        headerFrame.setLayout(headerLayout)

        execLayout = QGridLayout()
        execLayout.setContentsMargins(1, 1, 1, 1)
        execLayout.setSpacing(1)
        execLayout.addWidget(self.__execStatement, 0, 0)
        execLayout.addWidget(self.__execButton, 0, 1)

        verticalLayout.addWidget(headerFrame)
        verticalLayout.addWidget(self.__browser)
        verticalLayout.addLayout(execLayout)

    def __filterMenuAboutToShow(self):
        """Debug variable filter menu is about to show"""
        for flt in self.__filters:
            flt.setChecked(Settings()[flt.data()])

    def __filterMenuTriggered(self, act):
        """A filter has been changed"""
        name = act.data()
        if name == 'showall':
            for _, settingName, _ in VARIABLE_FILTERS:
                Settings()[settingName] = True
        else:
            Settings()[name] = not Settings()[name]
        self.__updateFilter()

    def updateVariables(self, areGlobals, frameNumber, variables):
        """Triggered when a new set of variables is received"""
        self.__browser.showVariables(areGlobals, variables, frameNumber)
        self.__updateHeaderLabel()

    def updateVariable(self, areGlobals, variables):
        """Triggered when a new variable has been received"""
        self.__browser.showVariable(areGlobals, variables)
        self.__updateHeaderLabel()

    def __updateHeaderLabel(self):
        """Updates the header text"""
        shown, total = self.__browser.getShownAndTotalCounts()
        if shown == 0 and total == 0:
            self.__headerLabel.setText("Variables")
        else:
            self.__headerLabel.setText("Variables (" + str(shown) +
                                       " of " + str(total) + ")")

    def __updateFilter(self):
        """Updates the current filter"""
        self.__browser.filterChanged()
        self.__updateHeaderLabel()

    def clear(self):
        """Clears the content"""
        self.__browser.clear()
        self.__updateHeaderLabel()

    def clearAll(self):
        """Clears everything including the history"""
        self.clear()
        self.__execStatement.lineEdit().setText("")
        self.__execStatement.clear()

    def __execStatementChanged(self, text):
        """Triggered when a exec statement is changed"""
        text = str(text).strip()
        self.__execButton.setEnabled(text != "")

    def __onEnterInExec(self):
        """Enter/return clicked in exec"""
        self.__onExec()

    def __onExec(self):
        """Triggered when the Exec button is clicked"""
        text = self.__execStatement.currentText().strip()
        if text != "":
            currentFrame = GlobalData().mainWindow.getCurrentFrameNumber()
            self.__debugger.remoteExecuteStatement(text, currentFrame)
            self.__debugger.remoteClientVariables(1, currentFrame)  # globals
            self.__debugger.remoteClientVariables(0, currentFrame)  # locals

    def switchControl(self, isInIDE):
        """Switches the UI depending where the control flow is"""
        self.__browser.setEnabled(isInIDE)
        self.__filterButton.setEnabled(isInIDE)

        self.__execStatement.setEnabled(isInIDE)
        if isInIDE:
            text = self.__execStatement.currentText().strip()
            self.__execButton.setEnabled(text != "")
        else:
            self.__execButton.setEnabled(False)
