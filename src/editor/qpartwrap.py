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

"""qutepart text editor component wrapper"""


from qutepart import Qutepart
from ui.qt import QPalette, pyqtSignal, QFont
from utils.globals import GlobalData
from utils.settings import Settings


class QutepartWrapper(Qutepart):

    """Convenience qutepart wrapper"""

    sigTextEditorZoom = pyqtSignal(int)

    def __init__(self, parent):
        Qutepart.__init__(self, parent)

        # Remove all the default margins
        self.delMargin('mark_area')
        self.delMargin('line_numbers')

        # The minimum possible zoom not to make the margin disappear
        skin = GlobalData().skin
        marginPointSize = skin['lineNumFont'].pointSize()
        mainAreaPointSize = skin['monoFont'].pointSize()
        self.__minZoom = (min(marginPointSize, mainAreaPointSize) - 1) * -1

        self.setFont(QFont(skin['monoFont']))

    def setPaper(self, paperColor):
        """Sets the new paper color"""
        palette = self.palette()
        palette.setColor(QPalette.Active, QPalette.Base, paperColor)
        palette.setColor(QPalette.Inactive, QPalette.Base, paperColor)
        self.setPalette(palette)

    def setColor(self, textColor):
        """Sets the new text color"""
        palette = self.palette()
        palette.setColor(QPalette.Active, QPalette.Text, textColor)
        palette.setColor(QPalette.Inactive, QPalette.Text, textColor)
        self.setPalette(palette)

    def onZoomIn(self):
        """Increases the font"""
        self.sigTextEditorZoom.emit(Settings()['zoom'] + 1)

    def onZoomOut(self):
        """Decreases the font"""
        newZoom = Settings()['zoom'] - 1
        if newZoom >= self.__minZoom:
            self.sigTextEditorZoom.emit(newZoom)

    def zoomTo(self, zoomVal):
        """Sets the zoom to a certain value if possible"""
        # zoomVal is an integer: > 0 => larger, < 0 => smaller than the base
        font = QFont(GlobalData().skin['monoFont'])
        zoomVal = max(zoomVal, self.__minZoom)
        fontSize = font.pointSize() + zoomVal
        font.setPointSize(fontSize)
        self.setFont(font)

        for margin in self.getMargins():
            if hasattr(margin, 'zoomTo'):
                margin.zoomTo(zoomVal)

    def clearUndoRedoHistory(self):
        """Clears the undo/redo history"""
        self.document().clearUndoRedoStacks()
