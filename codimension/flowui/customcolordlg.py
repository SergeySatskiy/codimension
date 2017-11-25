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

from ui.qt import (QDialog, QVBoxLayout, QGridLayout, QLabel, QDialogButtonBox,
                   Qt, QGraphicsRectItem, QPen, QBrush)
from ui.colorbutton import ColorButton


class CustomColorsDialog(QDialog):

    """Custom colors dialog implementation"""

    def __init__(self, bgcolor, fgcolor, bordercolor, parent=None):
        """colors are instances of QColor"""
        QDialog.__init__(self, parent)

        self.__createLayout()
        self.__bgColorButton.setColor(bgcolor.name())
        self.__bgColorButton.sigColorChanged.connect(self.__onColorChanged)
        self.__fgColorButton.setColor(fgcolor.name())
        self.__fgColorButton.sigColorChanged.connect(self.__onColorChanged)
        self.__borderColorButton.setColor(bordercolor.name())
        self.__borderColorButton.sigColorChanged.connect(self.__onColorChanged)

        self.__onColorChanged()

    def __createLayout(self):
        """Creates the dialog layout"""
        self.resize(600, 400)
        self.setSizeGripEnabled(True)

        verticalLayout = QVBoxLayout(self)
        gridLayout = QGridLayout()

        bgLabel = QLabel('Background color:', self)
        gridLayout.addWidget(bgLabel, 0, 0, 1, 1)
        self.__bgColorButton = ColorButton('Select')
        gridLayout.addWidget(self.__bgColorButton, 0, 1, 1, 1)

        fgLabel = QLabel('Foreground color:', self)
        gridLayout.addWidget(fgLabel, 1, 0. 1, 1)
        self.__fgColorButton = ColorButton('Select')
        gridLayout.addWidget(self.__fgColorButton, 1, 1, 1, 1)

        borderLabel = QLabel('Border color:', self)
        gridLayout.addWidget(borderLabel, 2, 0, 1, 1)
        self.__borderColorButton = ColorButton('Select')
        gridLayout.addWidget(self.__borderColorButton, 2, 1, 1, 1)

        verticalLayout.addLayout(gridLayout)

        # Sample area
        self.__scene = QGraphicsScene()
        self.__view = QGraphicsView()
        self.__view.setScene(self.__scene)
        verticalLayout.addWidget(self.__view)
        # self.scene.setSceneRect(0, 0, 500, 150)

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
        xPos = 10
        yPos = 10
        width = 150
        height = 40

        self.__scene.clear()
        block = SampleBlock()

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

    def __init__(self, settings, parent=None):
        QGraphicsRectItem.__init__(self, parent)
        self.__settings = settings

    def paint(self, painter, option, widget):
        """Draws the code block"""
        pen = QPen(self.__borderColor)
        painter.setPen(pen)
        brush = QBrush(self.__bgColor)
        painter.setBrush(brush)
        painter.drawRect(self.baseX + settings.hCellPadding,
                         self.baseY + settings.vCellPadding,
                         rectWidth, rectHeight)

        # Draw the text in the rectangle
        pen = QPen(self.__fgColor)
        painter.setFont(settings.monoFont)
        painter.setPen(pen)

        textWidth = self.__textRect.width() + 2 * settings.hTextPadding
        textShift = (rectWidth - textWidth) / 2
        painter.drawText(
            self.baseX + settings.hCellPadding +
            settings.hTextPadding + textShift,
            self.baseY + settings.vCellPadding + settings.vTextPadding,
            self.__textRect.width(), self.__textRect.height(),
            Qt.AlignLeft, 'Sample')
