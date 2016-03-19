#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy <sergey.satskiy@gmail.com>
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

" Control flow UI widget: handling keyboard events "

from PyQt4.QtCore import Qt, QPoint
from PyQt4.QtGui import QGraphicsScene
from sys import maxint
from flowui.items import CellElement
from flowui.scopeitems import ScopeCellElement


CTRL_SHIFT = int( Qt.ShiftModifier | Qt.ControlModifier )
SHIFT = int( Qt.ShiftModifier )
CTRL = int( Qt.ControlModifier )
ALT = int( Qt.AltModifier )
CTRL_KEYPAD = int( Qt.KeypadModifier | Qt.ControlModifier )
NO_MODIFIER = int( Qt.NoModifier )


class CFSceneKeyboardMixin:
    " Encapsulates keyboard handling and related functionality "

    def __init__( self ):
        self.__hotKeys = {
                CTRL:   { Qt.Key_QuoteLeft:     self.highlightInText,
                          Qt.Key_Home:          self.scrollToTop,
                          Qt.Key_End:           self.scrollToBottom,
                          Qt.Key_A:             self.selectAll
                         },
                NO_MODIFIER:
                        { Qt.Key_Home:          self.scrollToHBegin,
                          Qt.Key_End:           self.scrollToHEnd,
                          Qt.Key_Escape:        self.clearSelection
                        }
                         }
        return

    def keyPressEvent( self, event ):
        """ Handles the key press event """
        key = event.key()
        modifiers = int( event.modifiers() )
        if modifiers in self.__hotKeys:
            if key in self.__hotKeys[ modifiers ]:
                self.__hotKeys[ modifiers ][ key ]()
                event.accept()
                return

        QGraphicsScene.keyPressEvent( self, event )
        return

    def highlightInText( self ):
        " Sync the text with the graphics "
        view = self.parent().view
        visibleRect = view.getVisibleRect()

        firstLine = visibleRect.y()

        candidateAfter = None
        candidateAfterDistance = maxint
        candidateBefore = None
        candidateBeforeDistance = maxint * -1
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
            return

        self.clearSelection()
        logicalItem = item
        if item.scopedItem():
            if item.subKind in [ ScopeCellElement.DECLARATION ]:
                logicalItem = item.getTopLeftItem()
        logicalItem.setSelected( True )
        view.scrollTo( logicalItem )
        item.mouseDoubleClickEvent( None )
        return

    def scrollToTop( self ):
        view = self.parent().view
        view.horizontalScrollBar().setValue( 0 )
        view.verticalScrollBar().setValue( 0 )
        return

    def scrollToBottom( self ):
        view = self.parent().view
        view.horizontalScrollBar().setValue( 0 )
        view.verticalScrollBar().setValue( view.verticalScrollBar().maximum() )
        return

    def scrollToHBegin( self ):
        view = self.parent().view
        view.horizontalScrollBar().setValue( 0 )
        return

    def scrollToHEnd( self ):
        view = self.parent().view
        view.horizontalScrollBar().setValue( view.horizontalScrollBar().maximum() )
        return

    def selectAll( self ):
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
            for item in self.findItemsForRef( moduleItem.ref ):
                self.addToSelection( item )
        return

