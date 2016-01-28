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

""" Sets up the flow UI context menus """


from PyQt4.QtGui import QMenu
from flowui.items import IfCell


class CFSceneContextMenuMixin:
    " Encapsulates the context menu handling "

    def __init__( self ):
        self.menus = {}

        ifContextMenu = QMenu()
        switchBranchAction = ifContextMenu.addAction( "Switch branch layout" )
        switchBranchAction.triggered.connect( self.onswitchIfBranch )

        self.menus[ IfCell ] = ifContextMenu
        return

    def onswitchIfBranch( self ):
        " If primitive should switch the branches "
        print "Switch if branch"





