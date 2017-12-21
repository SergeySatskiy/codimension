# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Control flow UI navigation bar"""

from ui.qt import Qt, QWidget, QHBoxLayout, QLabel, QFrame, QSizePolicy
from utils.pixmapcache import getPixmap
from utils.colorfont import getLabelStyle


class ControlFlowNavigationBar(QFrame):

    """Navigation bar at the top of the flow UI widget"""

    STATE_OK_UTD = 0        # Parsed OK, control flow up to date
    STATE_OK_CHN = 1        # Parsed OK, control flow changed
    STATE_BROKEN_UTD = 2    # Parsed with errors, control flow up to date
    STATE_BROKEN_CHN = 3    # Parsed with errors, control flow changed
    STATE_UNKNOWN = 4

    def __init__(self, parent):
        QFrame.__init__(self, parent)
        self.__infoIcon = None
        self.__warningsIcon = None
        self.__layout = None
        self.__pathLabel = None
        self.__createLayout()
        self.__currentIconState = self.STATE_UNKNOWN

    def __createLayout(self):
        """Creates the layout"""
        self.setFixedHeight(24)
        self.__layout = QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)

        labelStylesheet = 'QLabel {' + getLabelStyle(self) + '}'

        # Create info icon
        self.__infoIcon = QLabel()
        self.__infoIcon.setPixmap(getPixmap('cfunknown.png'))
        self.__layout.addWidget(self.__infoIcon)

        self.__warningsIcon = QLabel()
        self.__warningsIcon.setPixmap(getPixmap('cfwarning.png'))
        self.__layout.addWidget(self.__warningsIcon)

        self.clearWarnings()

        # Create the path label
        self.__pathLabel = QLabel(self)
        self.__pathLabel.setStyleSheet(labelStylesheet)
        self.__pathLabel.setTextFormat(Qt.PlainText)
        self.__pathLabel.setAlignment(Qt.AlignLeft)
        self.__pathLabel.setWordWrap(False)
        self.__pathLabel.setTextInteractionFlags(Qt.NoTextInteraction)
        self.__pathLabel.setSizePolicy(QSizePolicy.Expanding,
                                       QSizePolicy.Fixed)
        self.__layout.addWidget(self.__pathLabel)

        self.__spacer = QWidget()
        self.__spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.__spacer.setMinimumWidth(0)
        self.__layout.addWidget(self.__spacer)

        # Create the selection label
        self.__selectionLabel = QLabel(self)
        self.__selectionLabel.setStyleSheet(labelStylesheet)
        self.__selectionLabel.setTextFormat(Qt.PlainText)
        self.__selectionLabel.setAlignment(Qt.AlignCenter)
        self.__selectionLabel.setWordWrap(False)
        self.__selectionLabel.setTextInteractionFlags(Qt.NoTextInteraction)
        self.__selectionLabel.setSizePolicy(QSizePolicy.Fixed,
                                            QSizePolicy.Fixed)
        self.__selectionLabel.setMinimumWidth(40)
        self.__layout.addWidget(self.__selectionLabel)
        self.setSelectionLabel(0, None)

    def clearWarnings(self):
        """Clears the warnings"""
        self.__warningsIcon.setVisible(False)
        self.__warningsIcon.setToolTip("")

    def setWarnings(self, warnings):
        """Sets the warnings"""
        self.__warningsIcon.setToolTip(
            'Control flow parser warnings:\n' + '\n'.join(warnings))
        self.__warningsIcon.setVisible(True)

    def clearErrors(self):
        """Clears all the errors"""
        self.__infoIcon.setToolTip('')

    def setErrors(self, errors):
        """Sets the errors"""
        self.__infoIcon.setToolTip(
            'Control flow parser errors:\n' + '\n'.join(errors))

    def updateInfoIcon(self, state):
        """Updates the information icon"""
        if state == self.__currentIconState:
            return

        if state == self.STATE_OK_UTD:
            self.__infoIcon.setPixmap(getPixmap('cfokutd.png'))
            self.__infoIcon.setToolTip("Control flow is up to date")
            self.__currentIconState = self.STATE_OK_UTD
        elif state == self.STATE_OK_CHN:
            self.__infoIcon.setPixmap(getPixmap('cfokchn.png'))
            self.__infoIcon.setToolTip("Control flow is not up to date; "
                                       "will be updated on idle")
            self.__currentIconState = self.STATE_OK_CHN
        elif state == self.STATE_BROKEN_UTD:
            self.__infoIcon.setPixmap(getPixmap('cfbrokenutd.png'))
            self.__infoIcon.setToolTip("Control flow might be invalid "
                                       "due to invalid python code")
            self.__currentIconState = self.STATE_BROKEN_UTD
        elif state == self.STATE_BROKEN_CHN:
            self.__infoIcon.setPixmap(getPixmap('cfbrokenchn.png'))
            self.__infoIcon.setToolTip("Control flow might be invalid; "
                                       "will be updated on idle")
            self.__currentIconState = self.STATE_BROKEN_CHN
        else:
            # STATE_UNKNOWN
            self.__infoIcon.setPixmap(getPixmap('cfunknown.png'))
            self.__infoIcon.setToolTip("Control flow state is unknown")
            self.__currentIconState = self.STATE_UNKNOWN

    def getCurrentState(self):
        """Provides the current state"""
        return self.__currentIconState

    def setPath(self, txt):
        """Sets the path label content"""
        self.__pathLabel.setText(txt)

    def setPathVisible(self, switchOn):
        """Sets the path visible"""
        self.__pathLabel.setVisible(switchOn)
        self.__spacer.setVisible(not switchOn)

    def setSelectionLabel(self, text, tooltip):
        """Sets selection label"""
        self.__selectionLabel.setText(str(text))
        if tooltip:
            self.__selectionLabel.setToolTip("Selected items:\n" +
                                             str(tooltip))
        else:
            self.__selectionLabel.setToolTip("Number of selected items")

    def resizeEvent(self, event):
        """Editor has resized"""
        QFrame.resizeEvent(self, event)
