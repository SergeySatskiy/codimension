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

"""Control flow UI widget: handling mouse events"""

from sys import maxsize
from flowui.scopeitems import ScopeCellElement
from flowui.items import CellElement
from flowui.auxitems import RubberBandItem
from ui.qt import Qt, QTransform, QPoint, QRect, QSize, QCursor, QGraphicsScene


# The default mouse behavior of the QT library is sometimes inconsistent.
# For example, selecting of the items is done on mousePressEvent however
# adding items is done on mouseReleaseEvent.
# One more problem is that the QT library does not support hierarchical
# relationships between the items. I.e. if an outer item is selected then
# it makes no sense to let nested items addable.
# The last problem is that there are proxy items (like badges) which are not
# supported out of the box obviously.
# So the whole mouse[Press,Release]Event members are overridden.
# The selection always works on mouse release event. Mouse press will do
# nothing.


RUBBER_BAND_MIN_SIZE = 5

class CFSceneMouseMixin:

    """Encapsulates mouse clicks handling and related functionality"""

    def __init__(self):
        self.lmbOrigin = None
        self.rubberBand = None

    @staticmethod
    def __getLogicalItem(item):
        """Provides a logical item or None"""
        if item is None:
            return None
        if item.isProxyItem():
            # This is for an SVG, a badge, a text and a connector
            return item.getProxiedItem()
        if not item.scopedItem():
            return item
        # Here: it is a scope item. Need to map/suppress in some cases
        if item.subKind in [ScopeCellElement.DECLARATION]:
            # Need to map to the top left item because the out
            return item.getTopLeftItem()
        if item.subKind in [ScopeCellElement.SIDE_COMMENT,
                            ScopeCellElement.DOCSTRING]:
            # No mapping
            return item
        # All the other scope items
        #   ScopeCellElement.TOP_LEFT, ScopeCellElement.LEFT,
        #   ScopeCellElement.BOTTOM_LEFT, ScopeCellElement.TOP,
        #   ScopeCellElement.BOTTOM
        # are to be ignored
        return None

    def __createRubberBand(self, event):
        """Creates the rubber band rectangle and shows it"""
        self.lmbOrigin = event.scenePos().toPoint()
        self.rubberBand = RubberBandItem(self.parent().cflowSettings)
        self.addItem(self.rubberBand)
        self.rubberBand.setGeometry(QRect(self.lmbOrigin, QSize()))
        self.rubberBand.hide()

    def __destroyRubberBand(self):
        """Destroys the rubber band selection rectangle"""
        if self.rubberBand is not None:
            self.rubberBand.hide()
            self.rubberBand = None
        self.lmbOrigin = None

    def mousePressEvent(self, event):
        """Handles mouse press event"""
        button = event.button()
        if button not in [Qt.LeftButton, Qt.RightButton]:
            self.clearSelection()
            event.accept()
            return

        if button == Qt.RightButton:
            item = self.itemAt(event.scenePos(), QTransform())
            logicalItem = self.__getLogicalItem(item)
            if logicalItem is None:
                # Not a selectable item or out of the items
                self.clearSelection()
            elif not logicalItem.isSelected():
                self.clearSelection()
                logicalItem.setSelected(True)

            # Bring up a context menu
            self.onContextMenu(event)
        else:
            # Here: this is LMB
            self.__createRubberBand(event)

        event.accept()
        return

    def mouseMoveEvent(self, event):
        """Handles mouse movement"""
        if self.lmbOrigin and self.rubberBand:
            # Draw the rubber band selection rectangle
            rect = QRect(self.lmbOrigin, event.scenePos().toPoint())
            self.rubberBand.setGeometry(rect.normalized())
            if not self.rubberBand.isVisible():
                if abs(rect.left() - rect.right()) >= RUBBER_BAND_MIN_SIZE or \
                   abs(rect.top() - rect.bottom()) >= RUBBER_BAND_MIN_SIZE:
                    self.rubberBand.show()
        QGraphicsScene.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        """Handles the mouse release event"""
        button = event.button()

        if button not in [Qt.LeftButton, Qt.RightButton]:
            event.accept()
            return

        if button == Qt.RightButton:
            event.accept()
            return

        # Here: left mouse button
        if self.rubberBand and self.rubberBand.isVisible():
            # Detect intersections
            self.clearSelection()
            for item in self.items():
                if item.isProxyItem():
                    continue
                if item.scopedItem():
                    if item.subKind not in [ScopeCellElement.DECLARATION,
                                            ScopeCellElement.SIDE_COMMENT,
                                            ScopeCellElement.DOCSTRING]:
                        continue

                    if item.subKind == ScopeCellElement.DECLARATION:
                        item = item.getTopLeftItem()

                # The call must be done on item. (not on rubberBand.)
                if item.collidesWithItem(self.rubberBand,
                                         Qt.ContainsItemBoundingRect):
                    self.addToSelection(item)
        else:
            item = self.itemAt(event.scenePos(), QTransform())
            logicalItem = self.__getLogicalItem(item)

            if logicalItem is None:
                self.clearSelection()
            else:
                modifiers = event.modifiers()
                if modifiers == Qt.NoModifier:
                    self.clearSelection()
                    logicalItem.setSelected(True)
                elif modifiers == Qt.ControlModifier:
                    if logicalItem.isSelected():
                        logicalItem.setSelected(False)
                    else:
                        # Item is not selected and should be added or ignored
                        self.addToSelection(logicalItem)
                # The alt modifier works for the whole app window on
                # Ubuntu, so it cannot really be used...
                elif modifiers == Qt.ShiftModifier:
                    self.clearSelection()

                    # Here: add comments
                    if self.isOpenGroupItem(item):
                        self.addToSelection(item)
                    else:
                        for item in self.findItemsForRef(logicalItem.ref):
                            self.addToSelection(item)

        self.__destroyRubberBand()
        event.accept()

    def addToSelection(self, item):
        """Adds an item to the current selection"""
        if self.isNestedInSelected(item):
            # Ignore the selection request
            return

        self.deselectNested(item)
        item.setSelected(True)

    def isNestedInSelected(self, itemToSelect):
        """Tells if the item is already included into some other selected"""
        toSelectBegin, toSelectEnd = self.__getItemVisualBeginEnd(itemToSelect)

        items = self.selectedItems()
        for item in items:
            isGroup = self.isOpenGroupItem(item)
            if not item.scopedItem() and not isGroup:
                continue
            if item.scopedItem():
                if item.subKind != ScopeCellElement.TOP_LEFT:
                    continue

            itemBegin, itemEnd = self.__getItemVisualBeginEnd(item)
            if toSelectBegin > itemBegin and toSelectEnd < itemEnd:
                return True
        return False

    def deselectNested(self, itemToSelect):
        """Deselects all the nested items if needed"""
        isGroup = itemToSelect.kind == CellElement.OPENED_GROUP_BEGIN
        if not itemToSelect.scopedItem() and not isGroup:
            # The only scope items and groups require
            # deselection of the nested items
            return
        if itemToSelect.scopedItem():
            if itemToSelect.subKind != ScopeCellElement.TOP_LEFT:
                # Scope docstrings and side comments cannot include anything
                return

        toSelectBegin, toSelectEnd = self.__getItemVisualBeginEnd(itemToSelect)
        items = self.selectedItems()
        for item in items:
            itemBegin, itemEnd = self.__getItemVisualBeginEnd(item)
            if itemBegin >= toSelectBegin and itemEnd <= toSelectEnd:
                item.setSelected(False)

    def __getItemVisualBeginEnd(self, item):
        """Provides the item visual begin and end"""
        if item.scopedItem():
            if item.subKind == ScopeCellElement.SIDE_COMMENT:
                return item.ref.sideComment.begin, item.ref.sideComment.end
            if item.subKind == ScopeCellElement.DOCSTRING:
                return item.ref.docstring.begin, item.ref.docstring.end
            # File scope differs from the other scopes
            if item.kind == CellElement.FILE_SCOPE:
                if item.ref.docstring:
                    return item.ref.docstring.begin, item.ref.body.end
                return item.ref.body.begin, item.ref.body.end

            # try, while, for are special
            if item.kind in [CellElement.TRY_SCOPE,
                             CellElement.FOR_SCOPE,
                             CellElement.WHILE_SCOPE]:
                lastSuiteItem = item.ref.suite[-1]
                return item.ref.body.begin, lastSuiteItem.end

            return item.ref.body.begin, item.ref.end

        # Here: not a scope item.
        if item.kind in [CellElement.ABOVE_COMMENT,
                         CellElement.LEADING_COMMENT]:
            return item.ref.leadingComment.begin, item.ref.leadingComment.end
        if item.kind == CellElement.SIDE_COMMENT:
            return item.ref.sideComment.begin, item.ref.sideComment.end
        if item.kind == CellElement.INDEPENDENT_COMMENT:
            return item.ref.begin, item.ref.end
        if item.kind == CellElement.ASSERT:
            if item.ref.message is not None:
                end = item.ref.message.end
            elif item.ref.test is not None:
                end = item.ref.test.end
            else:
                end = item.ref.body.end
            return item.ref.body.begin, end
        if item.kind == CellElement.RAISE:
            if item.ref.value is not None:
                end = item.ref.value.end
            else:
                end = item.ref.body.end
            return item.ref.body.begin, end
        if item.kind == CellElement.RETURN:
            if item.ref.value is not None:
                end = item.ref.value.end
            else:
                end = item.ref.body.end
            return item.ref.body.begin, end
        if item.kind in [CellElement.OPENED_GROUP_BEGIN,
                         CellElement.COLLAPSED_GROUP,
                         CellElement.EXCEPT_MINIMIZED]:
            begin, end = item.getAbsPosRange()
            return begin, end

        # if, import, sys.exit(), continue, break, code block
        return item.ref.body.begin, item.ref.body.end

    def findItemsForRef(self, ref):
        """Provides graphics items for the given ref"""
        result = []
        for item in self.items():
            if item.scopedItem():
                if item.subKind not in [ScopeCellElement.TOP_LEFT,
                                        ScopeCellElement.SIDE_COMMENT,
                                        ScopeCellElement.DOCSTRING]:
                    continue
            if not self.isOpenGroupItem(item):
                if hasattr(item, "ref"):
                    if item.ref is ref:
                        result.append(item)
        return result

    @staticmethod
    def isOpenGroupItem(item):
        """True if it is an open group item"""
        if hasattr(item, 'kind'):
            return item.kind == CellElement.OPENED_GROUP_BEGIN
        return False

    def getNearestItem(self, absPos, line, pos):
        """Provides a logical item and the distance.

        The item is the closest to the specified absPos, line:pos.
        The distance to the item (0 - within the item).
        line and pos are 1-based.
        """
        del pos     # unused argument
        candidates = []
        distance = maxsize

        for item in self.items():
            if item.isProxyItem():
                continue

            dist = item.getLineDistance(line)
            if dist == maxsize:
                continue    # Not really an option
            if dist < distance:
                distance = dist
                candidates = [item]
            elif dist == distance:
                candidates.append(item)

        count = len(candidates)
        if count == 0:
            return None, maxsize
        if count == 1:
            return self.__getLogicalItem(candidates[0]), distance

        # Here: more than one item with an equal distance
        #       There are two cases here: 0 and non zero distance
        if distance != 0:
            # It is pretty much not important which one to pick.
            # Let it be the first foun item
            return self.__getLogicalItem(candidates[0]), distance

        # This is a zero line distance, so a candidate should be the one with
        # the shortest position distance
        candidate = None
        distance = maxsize
        for item in candidates:
            dist = item.getDistance(absPos)
            if dist == 0:
                return self.__getLogicalItem(item), 0
            if dist < distance:
                distance = dist
                candidate = item
        return self.__getLogicalItem(candidate), distance
