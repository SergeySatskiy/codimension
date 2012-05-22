#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2011  Sergey Satskiy <sergey.satskiy@gmail.com>
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

""" The debugger namespace viewer implementation """

from PyQt4.QtCore import Qt, SIGNAL, QSize, QStringList, QModelIndex
from PyQt4.QtGui import QTextEdit, QMenu, QComboBox, \
                        QApplication, QCursor, QToolButton, \
                        QHBoxLayout, QWidget, QAction, QToolBar, \
                        QSizePolicy, QLabel, QVBoxLayout, QFrame, \
                        QTreeWidget, QAbstractItemView
from utils.pixmapcache import PixmapCache
from ui.itemdelegates  import NoOutlineHeightDelegate


class NamespaceViewer( QTreeWidget ):
    """ The debugger namespace viewer widget """

    def __init__( self, parent = None ):
        QTreeWidget.__init__( self, parent )

        self.setRootIsDecorated( True )
        self.setAlternatingRowColors( True )
        self.setUniformRowHeights( True )
        self.setItemDelegate( NoOutlineHeightDelegate( 4 ) )

        headerLabels = QStringList() << "Name" << "Type" << "Representation"
        self.setHeaderLabels( headerLabels )

        header = self.header()
        header.setSortIndicator( 0, Qt.AscendingOrder )
        header.setSortIndicatorShown( True )
        header.setClickable( True )

        self.setSortingEnabled( True )

        self.setSelectionMode( QAbstractItemView.SingleSelection )
        self.setSelectionBehavior( QAbstractItemView.SelectRows )

        self.header().setStretchLastSection( True )
        self.layoutDisplay()
        return

    def layoutDisplay( self ):
        " Performs the layout operation "
        self.doItemsLayout()
        self._resizeColumns( QModelIndex() )
        self._resort()
        return

    def _resizeColumns( self, index ):
        " Resizes the view when items get expanded or collapsed "

        rowCount = self.model().rowCount()
        self.header().setStretchLastSection( True )

        width = max( 100, self.sizeHintForColumn( 0 ) )
        self.header().resizeSection( 0, width )
        return

    def _resort( self ):
        " Re-sorts the tree "
        self.model().sort( self.header().sortIndicatorSection(),
                           self.header().sortIndicatorOrder() )
        return

