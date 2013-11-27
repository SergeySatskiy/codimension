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

""" Diff viewer tab widget """


from ui.mainwindowtabwidgetbase import MainWindowTabWidgetBase
from utils.settings import Settings
from htmltabwidget import HTMLTabWidget


class DiffTabWidget( HTMLTabWidget ):
    " The widget which displays a RO diff page "

    def __init__( self, parent = None ):
        HTMLTabWidget.__init__( self, parent )
        return

    def setHTML( self, content ):
        " Sets the content from the given string "
        HTMLTabWidget.setHTML( self, content )
        self.zoomTo( Settings().zoom )
        return

    def loadFormFile( self, path ):
        " Loads the content from the given file "
        HTMLTabWidget.loadFormFile( self, path )
        self.zoomTo( Settings().zoom )
        return

    def getType( self ):
        " Tells the widget type "
        return MainWindowTabWidgetBase.DiffViewer

    def getLanguage( self ):
        " Tells the content language "
        return "diff"
