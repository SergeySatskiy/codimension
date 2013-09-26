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

" Menu provider for codimension subversion plugin "


from PyQt4.QtCore import SIGNAL
import os.path
from svnindicators import IND_ERROR



def populateMainMenu( plugin, parentMenu ):
    " Populates subversion plugin main menu "
    plugin.connect( parentMenu, SIGNAL( "aboutToShow()" ),
                    plugin.onMainMenuAboutToShow )
    parentMenu.addAction( "Configure", plugin.configure )
    return

def populateFileContextMenu( plugin, parentMenu ):
    " Populates a context menu used for a file in a project browser "
    plugin.fileParentMenu = parentMenu
    plugin.connect( parentMenu, SIGNAL( "aboutToShow()" ),
                    plugin.onFileContextMenuAboutToShow )
    plugin.fileContextInfoAct = parentMenu.addAction( "&Info", plugin.fileInfo )
    plugin.fileContextUpdateAct = parentMenu.addAction( "&Update", plugin.fileUpdate )
    return

def populateDirectoryContextMenu( plugin, parentMenu ):
    " Populates a context menu used for a directory in a project browser "
    plugin.dirParentMenu = parentMenu
    plugin.connect( parentMenu, SIGNAL( "aboutToShow()" ),
                    plugin.onDirectoryContextMenuAboutToShow )
    plugin.dirContextInfoAct = parentMenu.addAction( "&Info", plugin.dirInfo )
    plugin.dirContextUpdateAct = parentMenu.addAction( "&Update", plugin.dirUpdate )
    return

def populateBufferContextMenu( plugin, parentMenu ):
    " Populates a context menu used for a text editor or a viewer "
    plugin.connect( parentMenu, SIGNAL( "aboutToShow()" ),
                    plugin.onBufferContextMenuAboutToshow )
    plugin.bufContextInfoAct = parentMenu.addAction( "&Info", plugin.bufferInfo )
    plugin.bufContextUpdateAct = parentMenu.addAction( "&Update", plugin.bufferUpdate )
    return



def mainMenuAboutToShow( plugin ):
    " Called when the plugin main menu is about to show "
    return

def fileContextMenuAboutToShow( plugin ):
    " Called when the plugin file context menu is about to show "
    path = str( plugin.fileParentMenu.menuAction().data().toString() )
    if plugin.getLocalStatus( path ) in [ plugin.NOT_UNDER_VCS,
                                          IND_ERROR ]:
        plugin.fileContextInfoAct.setEnabled( False )
        plugin.fileContextUpdateAct.setEnabled( False )
        return

    plugin.fileContextInfoAct.setEnabled( True )
    plugin.fileContextUpdateAct.setEnabled( True )
    return

def directoryContextMenuAboutToShow( plugin ):
    " Called when the plugin directory context manu is about to show "
    path = str( plugin.dirParentMenu.menuAction().data().toString() )
    if plugin.getLocalStatus( path ) in [ plugin.NOT_UNDER_VCS,
                                          IND_ERROR ]:
        plugin.dirContextInfoAct.setEnabled( False )
        plugin.dirContextUpdateAct.setEnabled( False )
        return

    plugin.dirContextInfoAct.setEnabled( True )
    plugin.dirContextUpdateAct.setEnabled( True )
    return

def bufferContextMenuAboutToshow( plugin ):
    " Called when the plugin buffer context menu is about to show "
    path = plugin.ide.currentEditorWidget.getFileName()
    if not os.path.isabs( path ):
        plugin.bufContextInfoAct.setEnabled( False )
        return
    if plugin.getLocalStatus( path ) in [ plugin.NOT_UNDER_VCS,
                                          IND_ERROR ]:
        plugin.bufContextInfoAct.setEnabled( False )
        plugin.bufContextUpdateAct.setEnabled( False )
        return

    plugin.bufContextInfoAct.setEnabled( True )
    plugin.bufContextUpdateAct.setEnabled( True )
    return

