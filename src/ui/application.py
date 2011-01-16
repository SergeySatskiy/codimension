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


""" definition of the codimension QT based application class """

from PyQt4.QtGui        import QApplication
from utils.pixmapcache  import PixmapCache


class CodimensionApplication( QApplication ):
    """ codimension application class """

    def __init__( self, argv ):
        QApplication.__init__( self, argv )
        QApplication.setStyle( 'plastique' )

        # FIXME: the icon looks black and white by some reasons at least on
        # Windows with X server
        QApplication.setWindowIcon( PixmapCache().getIcon( 'icon.png' ) )

        # Avoid having rectabgular frames on the status bar
        self.setStyleSheet( "QStatusBar::item { border: 0px solid black } " )
        return


