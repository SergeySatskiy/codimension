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

#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#

" Project browser model "


from PyQt4.QtCore       import SIGNAL
from PyQt4.QtCore       import QVariant
from viewitems          import TreeViewDirectoryItem
from utils.globals      import GlobalData
from utils.project      import CodimensionProject
from browsermodelbase   import BrowserModelBase


class ProjectBrowserModel( BrowserModelBase ):
    " Class implementing the project browser model "

    def __init__( self, parent = None ):
        BrowserModelBase.__init__( self, QVariant( "Name" ), parent )

        self.populateModel()

        self.connect( GlobalData().project, SIGNAL( 'projectChanged' ),
                      self.__onProjectChanged )
        return

    def populateModel( self ):
        " Populates the project browser model "

        self.clear()
        project = self.globalData.project
        if project.isLoaded():
            projectDir = project.getProjectDir()
            self.addItem( TreeViewDirectoryItem( self.rootItem, projectDir ) )
        return

    def __onProjectChanged( self, what ):
        " Triggered when a project is changed "

        if what == CodimensionProject.CompleteProject:
            self.populateModel()
        return

