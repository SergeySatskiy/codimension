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

"""Control flow UI graphics scene and a view"""

from ui.qt import (Qt, QRectF, QPoint, QPainter, QGraphicsView, QApplication,
                   QGraphicsScene)
from utils.settings import Settings
from .flowuicontextmenus import CFSceneContextMenuMixin
from .flowuimouse import CFSceneMouseMixin
from .flowuikeyboard import CFSceneKeyboardMixin



class CFGraphicsScene(QGraphicsScene,
                      CFSceneContextMenuMixin,
                      CFSceneMouseMixin,
                      CFSceneKeyboardMixin):

    """Reimplemented graphics scene"""

    def __init__(self, navBar, parent=None):
        QGraphicsScene.__init__(self, parent)
        CFSceneContextMenuMixin.__init__(self)
        CFSceneMouseMixin.__init__(self)
        CFSceneKeyboardMixin.__init__(self)
        self.__navBar = navBar
        self.selectionChanged.connect(self.selChanged)

    def selChanged(self):
        """Triggered when a selection changed"""
        items = self.sortSelectedReverse()
        items.reverse()
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


class CFGraphicsView(QGraphicsView):

    """Central widget"""

    def __init__(self, navBar, parent):
        super(CFGraphicsView, self).__init__(parent)
        self.scene = CFGraphicsScene(navBar, parent)
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

    def scrollTo(self, item, makeFirstOnScreen=False):
        """Scrolls the view to the item"""
        if item is None:
            return

        # When there is a change on the diagram, e.g. when a font was changed,
        # when a smart zoom was changed or a display mode was changed then
        # the sync between the views is done basing on what is the first
        # visible item. So the vertical scroll is required to make the item of
        # interest first on the screen

        visibleRect = self.getVisibleRect()
        itemRect = item.boundingRect()
        if not makeFirstOnScreen:
            if visibleRect.contains(itemRect):
                # The item is fully visible
                return

            # The item is fully visible vertically
            if itemRect.topLeft().y() >= visibleRect.topLeft().y() and \
               itemRect.bottomLeft().y() <= visibleRect.bottomLeft().y():
                self.__hScrollToItem(item)
                return

        # The item top left is visible
        if visibleRect.contains(itemRect.topLeft()):
            # So far scroll the view vertically anyway
            val = float(itemRect.topLeft().y() - 15.0)
            self.verticalScrollBar().setValue(val)
            self.__hScrollToItem(item)
            return

        # Here: the top left is not visible, so the vertical scrolling is
        # required
        val = float(itemRect.topLeft().y() - 15.0)
        self.verticalScrollBar().setValue(val)
        self.__hScrollToItem(item)

    def __hScrollToItem(self, item):
        """Sets the horizontal scrolling for the item"""
        if item is None:
            return

        # There are a few cases here:
        # - the item does not fit the screen width
        # - the item fits the screen width and would be visible if the
        #   scroll is set to 0
        # - the item fits the screen width and would not be visible if the
        #   scroll is set to 0

        visibleRect = self.getVisibleRect()
        itemRect = item.boundingRect()

        if itemRect.width() > visibleRect.width():
            # Does not fit the screen
            val = float(itemRect.topLeft().x()) - 15.0
            self.horizontalScrollBar().setValue(val)
        else:
            if itemRect.topRight().x() < visibleRect.width():
                # Fits the screen if the scroll is 0
                self.horizontalScrollBar().setValue(0)
            else:
                val = float(itemRect.topLeft().x()) - 15.0
                self.horizontalScrollBar().setValue(val)
