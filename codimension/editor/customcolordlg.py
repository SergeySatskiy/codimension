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
                   QGraphicsView, QTimer)
from ui.colorbutton import ColorButton
from flowui.cflowsettings import getCflowSettings
from utils.pixmapcache import getIcon


class CustomColorsDialog(QDialog):

    """Custom colors dialog implementation"""

    def __init__(self, bgcolor, fgcolor, bordercolor, parent=None):
        """colors are instances of QColor"""
        QDialog.__init__(self, parent)
        self.setWindowTitle('Custom colors')

        self.__createLayout()
        self.__bgColorButton.setColor(bgcolor)
        self.__bgColorButton.sigColorChanged.connect(self.__onColorChanged)
        self.__fgColorButton.setColor(fgcolor)
        self.__fgColorButton.sigColorChanged.connect(self.__onColorChanged)
        if bordercolor is None:
            self.__borderColorButton.setEnabled(False)
            self.__borderColorButton.setToolTip(
                'Border colors are not supported for docstrings')
            self.__borderColorButton.setIcon(getIcon('warning.png'))
        else:
            self.__borderColorButton.setColor(bordercolor)
            self.__borderColorButton.sigColorChanged.connect(self.__onColorChanged)

        QTimer.singleShot(1, self.__onColorChanged)

    def __createLayout(self):
        """Creates the dialog layout"""
        self.setMinimumWidth(300)
        self.setMinimumHeight(200)
        self.resize(300, 200)
        self.setSizeGripEnabled(True)

        verticalLayout = QVBoxLayout(self)
        verticalLayout.setContentsMargins(5, 5, 5, 5)
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
        viewWidth = self.__view.width()
        viewHeight = self.__view.height()

        self.__scene.clear()
        # without '-4' scrollbar will appear
        self.__scene.setSceneRect(0, 0, viewWidth - 4, viewHeight - 4)
        block = SampleBlock(getCflowSettings(self),
                            self.backgroundColor(),
                            self.foregroundColor(),
                            self.borderColor(),
                            viewWidth, viewHeight)
        self.__scene.addItem(block)
        self.__scene.update()

    def backgroundColor(self):
        """Provides the background color"""
        return self.__bgColorButton.color()

    def foregroundColor(self):
        """Provides the foreground color"""
        return self.__fgColorButton.color()

    def borderColor(self):
        """Provides the border color"""
        return self.__borderColorButton.color()


class SampleBlock(QGraphicsRectItem):

    """Sample block"""

    def __init__(self, settings, bgColor, fgColor, borderColor, width, height):
        QGraphicsRectItem.__init__(self)
        self.__settings = settings
        self.__bgColor = bgColor
        self.__fgColor = fgColor
        self.__borderColor = borderColor
        self.__viewWidth = width
        self.__viewHeight = height

        self.__textRect = self.__settings.monoFontMetrics.boundingRect(
            0, 0, maxsize, maxsize, 0, 'Sample')


        vPadding = 2 * settings.vTextPadding
        self.__rectHeight = self.__textRect.height() + vPadding
        hPadding = 2 * settings.hTextPadding
        self.__rectWidth = max(self.__textRect.width() + hPadding,
                               settings.minWidth)

    def paint(self, painter, option, widget):
        """Draws the code block"""
        baseX = (self.__viewWidth - self.__rectWidth) / 2
        baseY = (self.__viewHeight - self.__rectHeight) / 2

        if self.__borderColor is None:
            pen = QPen(self.__bgColor)
        else:
            pen = QPen(self.__borderColor)
        painter.setPen(pen)
        brush = QBrush(self.__bgColor)
        painter.setBrush(brush)
        painter.drawRect(baseX, baseY, self.__rectWidth, self.__rectHeight)

        # Draw the text in the rectangle
        pen = QPen(self.__fgColor)
        painter.setFont(self.__settings.monoFont)
        painter.setPen(pen)

        textWidth = self.__textRect.width() + 2 * self.__settings.hTextPadding
        textShift = (self.__rectWidth - textWidth) / 2
        painter.drawText(baseX + self.__settings.hTextPadding + textShift,
                         baseY + self.__settings.vTextPadding,
                         self.__textRect.width(), self.__textRect.height(),
                         Qt.AlignLeft, 'Sample')
