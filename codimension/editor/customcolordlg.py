# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""custom colors dialog"""

from sys import maxsize
from ui.qt import (QDialog, QVBoxLayout, QGridLayout, QLabel, QDialogButtonBox,
                   Qt, QGraphicsRectItem, QPen, QBrush, QGraphicsScene,
                   QGraphicsView)
from ui.colorbutton import ColorButton
from flowui.cflowsettings import getCflowSettings


class CustomColorsDialog(QDialog):

    """Custom colors dialog implementation"""

    def __init__(self, bgcolor, fgcolor, bordercolor, parent=None):
        """colors are instances of QColor"""
        QDialog.__init__(self, parent)

        self.__createLayout()
        self.__bgColorButton.setColor(bgcolor)
        self.__bgColorButton.sigColorChanged.connect(self.__onColorChanged)
        self.__fgColorButton.setColor(fgcolor)
        self.__fgColorButton.sigColorChanged.connect(self.__onColorChanged)
        self.__borderColorButton.setColor(bordercolor)
        self.__borderColorButton.sigColorChanged.connect(self.__onColorChanged)

        self.__onColorChanged()

    def __createLayout(self):
        """Creates the dialog layout"""
        self.resize(400, 200)
        # self.setSizeGripEnabled(True)

        verticalLayout = QVBoxLayout(self)
        gridLayout = QGridLayout()

        bgLabel = QLabel('Select background color:', self)
        gridLayout.addWidget(bgLabel, 0, 0, 1, 1)
        self.__bgColorButton = ColorButton('', self)
        gridLayout.addWidget(self.__bgColorButton, 0, 1, 1, 1)

        fgLabel = QLabel('Select foreground color:', self)
        gridLayout.addWidget(fgLabel, 1, 0, 1, 1)
        self.__fgColorButton = ColorButton('', self)
        gridLayout.addWidget(self.__fgColorButton, 1, 1, 1, 1)

        borderLabel = QLabel('Select border color:', self)
        gridLayout.addWidget(borderLabel, 2, 0, 1, 1)
        self.__borderColorButton = ColorButton('', self)
        gridLayout.addWidget(self.__borderColorButton, 2, 1, 1, 1)

        verticalLayout.addLayout(gridLayout)

        # Sample area
        self.__scene = QGraphicsScene()
        self.__view = QGraphicsView()
        self.__view.setScene(self.__scene)
        verticalLayout.addWidget(self.__view)
        #self.__scene.setSceneRect(0, 0, 300, 100)

        # Buttons at the bottom
        buttonBox = QDialogButtonBox(self)
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Cancel |
                                     QDialogButtonBox.Ok)
        verticalLayout.addWidget(buttonBox)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

    def __onColorChanged(self):
        """The user changed the color so redraw the sample"""
        self.__scene.clear()
        block = SampleBlock(getCflowSettings(self),
                            self.backgroundColor(),
                            self.foreroundColor(),
                            self.borderColor())
        self.__scene.addItem(block)

    def backgroundColor(self):
        """Provides the background color"""
        return self.__bgColorButton.color()

    def foreroundColor(self):
        """Provides the foreground color"""
        return self.__fgColorButton.color()

    def borderColor(self):
        """Provides the border color"""
        return self.__borderColorButton.color()


class SampleBlock(QGraphicsRectItem):

    """Sample block"""

    def __init__(self, settings, bgColor, fgColor, borderColor, parent=None):
        QGraphicsRectItem.__init__(self, parent)
        self.__settings = settings
        self.__bgColor = bgColor
        self.__fgColor = fgColor
        self.__borderColor = borderColor

        self.baseX = 0
        self.baseY = 0

        self.__textRect = self.__settings.monoFontMetrics.boundingRect(
            0, 0, maxsize, maxsize, 0, 'Sample')
        vPadding = 2 * (settings.vCellPadding + settings.vTextPadding)
        self.minHeight = self.__textRect.height() + vPadding
        hPadding = 2 * (settings.hCellPadding + settings.hTextPadding)
        self.minWidth = max(self.__textRect.width() + hPadding,
                            settings.minWidth)

    def paint(self, painter, option, widget):
        """Draws the code block"""
        rectWidth = self.minWidth - 2 * self.__settings.hCellPadding
        rectHeight = self.minHeight - 2 * self.__settings.vCellPadding

        pen = QPen(self.__borderColor)
        painter.setPen(pen)
        brush = QBrush(self.__bgColor)
        painter.setBrush(brush)
        painter.drawRect(self.baseX + self.__settings.hCellPadding,
                         self.baseY + self.__settings.vCellPadding,
                         rectWidth, rectHeight)

        # Draw the text in the rectangle
        pen = QPen(self.__fgColor)
        painter.setFont(self.__settings.monoFont)
        painter.setPen(pen)

        textWidth = self.__textRect.width() + 2 * self.__settings.hTextPadding
        textShift = (rectWidth - textWidth) / 2
        painter.drawText(
            self.baseX + self.__settings.hCellPadding +
            self.__settings.hTextPadding + textShift,
            self.baseY + self.__settings.vCellPadding + self.__settings.vTextPadding,
            self.__textRect.width(), self.__textRect.height(),
            Qt.AlignLeft, 'Sample')
