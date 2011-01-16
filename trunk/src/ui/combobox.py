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
# $Id$
#

""" QComboBox extension:
    - memorizes the entry when the focus is lost
    - allows editing
    - limits the number of saved entries
    - does not allow duplications
    - disables auto completion
    - inserts items at top
"""


from PyQt4.QtCore import Qt
from PyQt4.QtGui  import QComboBox


class CDMComboBox( QComboBox ):
    " QComboBox extension for loosing a focus "

    itemsLimit = 16

    def __init__( self, parent = None ):
        QComboBox.__init__( self, parent )
        self.setEditable( True )
        self.setAutoCompletion( False )
        self.setDuplicatesEnabled( False )
        self.setInsertPolicy( QComboBox.InsertAtTop )
        return

    def focusOutEvent( self, event ):
        " Triggered when the widget lost its focus "

        text = self.lineEdit().text()
        if len( str( text ).strip() ) > 0:
            if self.findText( text, Qt.MatchFixedString ) == -1:
                self.insertItem( 0, text )
                self.__enforceLimit()
        return

    def keyReleaseEvent( self, event ):
        " Triggered when a key is released "
        QComboBox.keyReleaseEvent( self, event )
        key = event.key()
        if key == Qt.Key_Enter or key == Qt.Key_Return:
            self.__enforceLimit()
        return

    def __enforceLimit( self ):
        " checks the number of memorized items "
        # Check that the number of items is not exceeded
        while self.count() > self.itemsLimit:
            self.removeItem( self.count() - 1 )
        return

