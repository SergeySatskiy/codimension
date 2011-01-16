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

" ItemDelegate which helps changing the standard row height "


from PyQt4.QtCore       import QSize
from PyQt4.QtGui        import QItemDelegate, QStyledItemDelegate, \
                               QStyleOptionViewItem, QStyle


class ChangingHeightItemDelegate( QItemDelegate ):
    " Helper class to set rows height "

    def __init__( self, delta ):
        QItemDelegate.__init__( self )
        self.delta = delta
        self.lastHeight = 0
        return

    def sizeHint( self, option, index ):
        " Returns the size hint in which the only height matters "

        origSize = QItemDelegate.sizeHint( self, option, index )
        self.lastHeight = origSize.height() + self.delta
        return QSize( origSize.width(), self.lastHeight )


class NoOutlineDelegate( QStyledItemDelegate ):
    " Hides the dotted line outline around tree view cells "

    def __init__( self ):
        QStyledItemDelegate.__init__( self )
        return

    def paint( self, painter, option, index ):
        " Hides the dotted outline "

        itemOption = QStyleOptionViewItem( option )
        if itemOption.state & QStyle.State_HasFocus != 0:
            itemOption.state = itemOption.state & ~QStyle.State_HasFocus
        QStyledItemDelegate.paint( self, painter, itemOption, index )
        return


class NoOutlineHeightDelegate( QStyledItemDelegate ):
    " Changes the raw height and removes the dotted cells outline "

    def __init__( self, delta ):
        self.delta = delta
        self.lastHeight = 0
        QStyledItemDelegate.__init__( self )
        return

    def paint( self, painter, option, index ):
        " Hides the dotted outline "

        itemOption = QStyleOptionViewItem( option )
        if itemOption.state & QStyle.State_HasFocus != 0:
            itemOption.state = itemOption.state & ~QStyle.State_HasFocus
        QStyledItemDelegate.paint( self, painter, itemOption, index )
        return

    def sizeHint( self, option, index ):
        " Returns the size hint in which the only height matters "

        origSize = QStyledItemDelegate.sizeHint( self, option, index )
        self.lastHeight = origSize.height() + self.delta
        return QSize( origSize.width(), self.lastHeight )

