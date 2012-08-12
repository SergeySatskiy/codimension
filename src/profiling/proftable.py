#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2012  Sergey Satskiy <sergey.satskiy@gmail.com>
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

" Profiling results as a table "


from PyQt4.QtCore import SIGNAL, QStringList
from PyQt4.QtGui import QTreeWidgetItem, QTreeWidget
from ui.itemdelegates import NoOutlineHeightDelegate


class ProfilingTableItem( QTreeWidgetItem ):
    " Profiling table row "

    def __init__( self, items ):
        QTreeWidgetItem.__init__( self, items )

    def __lt__( self, other ):
        " Integer or string sorting "
        sortColumn = self.treeWidget().sortColumn()
        txt = self.text( sortColumn )
        otherTxt = other.text( sortColumn )
        try:
            val = int( txt )
            otherVal = int( otherTxt )
            return val < otherVal
        except:
            pass
        return txt < otherTxt


class ProfileTableViewer( QTreeWidget ):
    " Profiling results table viewer "

    def __init__( self, parent = None ):
        QTreeWidget.__init__( self, parent )

        self.setAlternatingRowColors( True )
        self.setRootIsDecorated( False )
        self.setItemsExpandable( False )
        self.setSortingEnabled( True )
        self.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        self.setUniformRowHeights( True )
        headerLabels = QStringList() << "# of calls" << "File name/line" << "Function"
        self.setHeaderLabels( headerLabels )
        self.connect( self, SIGNAL( "itemActivated(QTreeWidgetItem *, int)" ),
                      self.__activated )


    def __activated( self, item, column ):
        " Triggered when the item is activated "

        print "Item activated"
        return

    def __createItem( self, calls, fileName, line, function ):
        " Creates an item to display "
        pass

