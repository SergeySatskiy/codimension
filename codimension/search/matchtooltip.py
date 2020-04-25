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

from utils.colorfont import getZoomedMonoFont
from ui.qt import (Qt, QTimer, QCursor, QLabel, QFrame, QApplication,
                   QToolTip, QPalette, QColor, QVBoxLayout)


class MatchTooltip(QFrame):

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

        self.__cellHeight = 20     # default
        self.__screenWidth = 600   # default

        # On slow network connections when XServer is used the cursor movement
        # is delivered with a considerable delay which causes improper tooltip
        # displaying. This global variable prevents improper displaying.
        self.__inside = False

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

    def setCellHeight(self, height):
        """Sets the cell height"""
        self.__cellHeight = height

    def setScreenWidth(self, width):
        """Sets the screen width"""
        self.__screenWidth = width

    def setInside(self, inside):
        """Sets the inside flag"""
        self.__inside = inside

    def isInside(self):
        """Provides the inside flag"""
        return self.__inside

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
        if pos.x() + self.sizeHint().width() >= self.__screenWidth:
            pos.setX(self.__screenWidth - self.sizeHint().width() - 2)
        pos.setY(pos.y() - self.__cellHeight - 1 - self.sizeHint().height())
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
        if self.__inside:
            self.move(self.__getTooltipPos())
            self.raise_()
            QFrame.show(self)

