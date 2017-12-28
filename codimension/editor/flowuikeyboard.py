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

"""Control flow UI widget: handling keyboard events"""

from sys import maxsize
from ui.qt import Qt, QGraphicsScene
from flowui.items import CellElement
from flowui.scopeitems import ScopeCellElement
from utils.settings import Settings


CTRL_SHIFT = int(Qt.ShiftModifier | Qt.ControlModifier)
SHIFT = int(Qt.ShiftModifier)
CTRL = int(Qt.ControlModifier)
ALT = int(Qt.AltModifier)
CTRL_KEYPAD = int(Qt.KeypadModifier | Qt.ControlModifier)
NO_MODIFIER = int(Qt.NoModifier)


class CFSceneKeyboardMixin:

    """Encapsulates keyboard handling and related functionality"""

    def __init__(self):
        self.__hotKeys = {
            CTRL: {
                Qt.Key_QuoteLeft: self.highlightInText,
                Qt.Key_Home: self.scrollToTop,
                Qt.Key_End: self.scrollToBottom,
                Qt.Key_A: self.selectAll,
                Qt.Key_Minus: Settings().onFlowZoomOut,
                Qt.Key_Equal: Settings().onFlowZoomIn,
                Qt.Key_0: Settings().onFlowZoomReset},
            NO_MODIFIER: {
                Qt.Key_Home: self.scrollToHBegin,
                Qt.Key_End: self.scrollToHEnd,
                Qt.Key_Escape: self.clearSelection}}

    def keyPressEvent(self, event):
        """Handles the key press event"""
        key = event.key()
        modifiers = int(event.modifiers())
        if modifiers in self.__hotKeys:
            if key in self.__hotKeys[modifiers]:
                self.__hotKeys[modifiers][key]()
                event.accept()
                return
        QGraphicsScene.keyPressEvent(self, event)

    def highlightInText(self):
        """Sync the text with the graphics"""
        firstItem = self.getFirstLogicalItem()
        if firstItem:
            self.clearSelection()
            firstItem.setSelected(True)
            self.parent().view().scrollTo(firstItem)
            firstItem.mouseDoubleClickEvent(None)

    def getFirstLogicalItem(self):
        """Provides the first visible on the screen logical item"""
        view = self.parent().view()
        visibleRect = view.getVisibleRect()

        firstLine = visibleRect.y()

        candidateAfter = None
        candidateAfterDistance = maxsize
        candidateBefore = None
        candidateBeforeDistance = maxsize * -1
        for item in self.items():
            if item.isProxyItem():
                continue

            itemY = item.boundingRect().topLeft().y()

            dist = itemY - firstLine
            if dist > 0:
                if dist < candidateAfterDistance:
                    candidateAfterDistance = dist
                    candidateAfter = item
            elif dist > candidateBeforeDistance:
                candidateBeforeDistance = dist
                candidateBefore = item

        item = None
        if candidateAfter:
            item = candidateAfter
        elif candidateBefore:
            item = candidateBefore
        else:
            # No suitable item to select
            return None

        logicalItem = item
        if item.scopedItem():
            if item.subKind in [ScopeCellElement.DECLARATION]:
                logicalItem = item.getTopLeftItem()
        return logicalItem

    def scrollToTop(self):
        """Scrolls the view to the top"""
        view = self.parent().view()
        view.horizontalScrollBar().setValue(0)
        view.verticalScrollBar().setValue(0)

    def scrollToBottom(self):
        """Scrolls the view to the bottom"""
        view = self.parent().view()
        view.horizontalScrollBar().setValue(0)
        view.verticalScrollBar().setValue(view.verticalScrollBar().maximum())

    def scrollToHBegin(self):
        """Scrolls horizontally to the very beginning"""
        view = self.parent().view()
        view.horizontalScrollBar().setValue(0)

    def scrollToHEnd(self):
        """Scrolls horizontally to the very end"""
        view = self.parent().view()
        view.horizontalScrollBar().setValue(
            view.horizontalScrollBar().maximum())

    def selectAll(self):
        """Selects all"""
        moduleItem = None
        for item in self.items():
            if item.isProxyItem():
                continue
            if item.kind == CellElement.FILE_SCOPE:
                if item.subKind == ScopeCellElement.TOP_LEFT:
                    moduleItem = item
                    break

        if moduleItem:
            self.clearSelection()
            for item in self.findItemsForRef(moduleItem.ref):
                self.addToSelection(item)

    def onZoomOut(self):
        """Zoom out the view"""
        view = self.parent().view()
        view.zoomOut()

    def onZoomIn(self):
        """Zoom in the view"""
        view = self.parent().view()
        view.zoomIn()
