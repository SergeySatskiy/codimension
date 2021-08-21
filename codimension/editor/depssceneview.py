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

"""Dependencies UI graphics scene and a view"""

from ui.qt import (Qt, QRectF, QPoint, QPainter, QGraphicsView, QApplication,
                   QGraphicsScene)
from utils.settings import Settings



class DepsGraphicsScene(QGraphicsScene):

    """Reimplemented graphics scene"""

    def __init__(self, navBar, parent=None):
        QGraphicsScene.__init__(self, parent)
        self.__navBar = navBar
        self.selectionChanged.connect(self.selChanged)

    def selChanged(self):
        """Triggered when a selection changed"""
        items = self.selectedItems()
        count = len(items)
        if count:
            tooltip = []
            for item in items:
                if hasattr(item, "getSelectTooltip"):
                    tooltip.append(item.getSelectTooltip())
                else:
                    tooltip.append(str(type(item)))
            self.__navBar.setSelectionLabel(count, "\n".join(tooltip))
        else:
            self.__navBar.setSelectionLabel(0, None)

    def serializeSelection(self):
        """Builds a list of pairs: (id->int, tooltip->str)"""
        selection = []
        for item in self.selectedItems():
            selection.append((item.itemID, item.getSelectTooltip()))
        return selection

    # The selection can be restored by item IDs if the number of items on the
    # diagram has not changed. E.g. when zoom is done or a cml comment is
    # added/removed
    def restoreSelectionByID(self, selection):
        """Restores the selection by the item ID"""
        if selection:
            ids = [item[0] for item in selection]
            for item in self.items():
                if hasattr(item, "itemID"):
                    if item.itemID in ids:
                        item.setSelected(True)

    # The selection can be restored by item tooltips if there is no text
    # modifications but there are representation changes. E.g. the selection
    # can be roughly preserved between the smart zoom levels or when except
    # blocks are hidden/shown
    def restoreSelectionByTooltip(self, selection):
        """Restores the selection by the item tooltip"""
        if selection:
            tooltips = [item[1] for item in selection]
            for item in self.items():
                if hasattr(item, "getSelectTooltip"):
                    if item.getSelectTooltip() in tooltips:
                        item.setSelected(True)

    def terminate(self):
        """Called when a tab is closed"""
        self.selectionChanged.disconnect(self.selChanged)
        self.clear()



class DepsGraphicsView(QGraphicsView):

    """Central widget"""

    def __init__(self, navBar, parent):
        super(DepsGraphicsView, self).__init__(parent)
        self.scene = DepsGraphicsScene(navBar, parent)
        self.setScene(self.scene)

        self.__parentWidget = parent
        self.__currentFactor = 1.0
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)

    def wheelEvent(self, event):
        """Mouse wheel event"""
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            angleDelta = event.angleDelta()
            if not angleDelta.isNull():
                if angleDelta.y() > 0:
                    Settings().onFlowZoomIn()
                else:
                    Settings().onFlowZoomOut()
            event.accept()
        elif modifiers == Qt.ShiftModifier:
            angleDelta = event.angleDelta()
            if not angleDelta.isNull():
                if angleDelta.y() > 0:
                    self.__parentWidget.onSmartZoomLevelUp()
                else:
                    self.__parentWidget.onSmartZoomLevelDown()
            event.accept()
        else:
            QGraphicsView.wheelEvent(self, event)

    def getVisibleRect(self):
        """Provides the visible rectangle"""
        topLeft = self.mapToScene(QPoint(0, 0))
        bottomRight = self.mapToScene(QPoint(self.viewport().width(),
                                             self.viewport().height()))
        return QRectF(topLeft, bottomRight)

    def terminate(self):
        """Called when a tab is closed"""
        self.scene.terminate()
        self.scene.deleteLater()
