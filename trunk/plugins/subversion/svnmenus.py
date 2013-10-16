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
from svnindicators import ( IND_ERROR, IND_ADDED, IND_DELETED, IND_MERGED,
                            IND_MODIFIED_LR, IND_MODIFIED_L,
                            IND_REPLACED, IND_CONFLICTED )
from ui.mainwindowtabwidgetbase import MainWindowTabWidgetBase



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
    plugin.fileContextAnnotateAct = parentMenu.addAction( "&Annotate", plugin.fileAnnotate )
    plugin.fileContextAddAct = parentMenu.addAction( "A&dd to repository", plugin.fileAddToRepository )
    plugin.fileContextCommitAct = parentMenu.addAction( "&Commit...", plugin.fileCommit )
    return

def populateDirectoryContextMenu( plugin, parentMenu ):
    " Populates a context menu used for a directory in a project browser "
    plugin.dirParentMenu = parentMenu
    plugin.connect( parentMenu, SIGNAL( "aboutToShow()" ),
                    plugin.onDirectoryContextMenuAboutToShow )
    plugin.dirContextInfoAct = parentMenu.addAction( "&Info", plugin.dirInfo )
    plugin.dirContextUpdateAct = parentMenu.addAction( "&Update", plugin.dirUpdate )
    plugin.dirContextAddAct = parentMenu.addAction( "A&dd to repository", plugin.dirAddToRepository )
    plugin.dirContextAddRecursiveAct = parentMenu.addAction( "Add to repository recursively", plugin.dirAddToRepositoryRecursively )
    plugin.dirContextCommitAct = parentMenu.addAction( "&Commit...", plugin.dirCommit )
    return

def populateBufferContextMenu( plugin, parentMenu ):
    " Populates a context menu used for a text editor or a viewer "
    plugin.connect( parentMenu, SIGNAL( "aboutToShow()" ),
                    plugin.onBufferContextMenuAboutToshow )
    plugin.bufContextInfoAct = parentMenu.addAction( "&Info", plugin.bufferInfo )
    plugin.bufContextUpdateAct = parentMenu.addAction( "&Update", plugin.bufferUpdate )
    plugin.bufContextAnnotateAct = parentMenu.addAction( "&Annotate", plugin.bufferAnnotate )
    plugin.bufContextAddAct = parentMenu.addAction( "A&dd to repository", plugin.bufferAddToRepository )
    plugin.bufContextCommitAct = parentMenu.addAction( "&Commit...", plugin.bufferCommit )
    return



def mainMenuAboutToShow( plugin ):
    " Called when the plugin main menu is about to show "
    return

def fileContextMenuAboutToShow( plugin ):
    " Called when the plugin file context menu is about to show "
    path = str( plugin.fileParentMenu.menuAction().data().toString() )
    pathStatus = plugin.getLocalStatus( path )
    if pathStatus == IND_ERROR:
        plugin.fileContextInfoAct.setEnabled( False )
        plugin.fileContextUpdateAct.setEnabled( False )
        plugin.fileContextAnnotateAct.setEnabled( False )
        plugin.fileContextAddAct.setEnabled( False )
        plugin.fileContextCommitAct.setEnabled( False )
        return

    if pathStatus == plugin.NOT_UNDER_VCS:
        plugin.fileContextInfoAct.setEnabled( False )
        plugin.fileContextUpdateAct.setEnabled( False )
        plugin.fileContextAnnotateAct.setEnabled( False )
        plugin.fileContextCommitAct.setEnabled( False )

        upperDirStatus = plugin.getLocalStatus( os.path.dirname( path ) )
        if upperDirStatus == plugin.NOT_UNDER_VCS:
            plugin.fileContextAddAct.setEnabled( False )
        else:
            plugin.fileContextAddAct.setEnabled( upperDirStatus != IND_ERROR )
        return

    plugin.fileContextInfoAct.setEnabled( True )
    plugin.fileContextUpdateAct.setEnabled( True )
    plugin.fileContextAnnotateAct.setEnabled( True )
    plugin.fileContextAddAct.setEnabled( False )
    plugin.fileContextCommitAct.setEnabled( pathStatus in [
                    IND_ADDED, IND_DELETED, IND_MERGED, IND_MODIFIED_LR,
                    IND_MODIFIED_L, IND_REPLACED, IND_CONFLICTED ] )
    return

def directoryContextMenuAboutToShow( plugin ):
    " Called when the plugin directory context manu is about to show "
    path = str( plugin.dirParentMenu.menuAction().data().toString() )
    pathStatus = plugin.getLocalStatus( path )
    if pathStatus == IND_ERROR:
        plugin.dirContextInfoAct.setEnabled( False )
        plugin.dirContextUpdateAct.setEnabled( False )
        plugin.dirContextAddAct.setEnabled( False )
        plugin.dirContextAddRecursiveAct.setEnabled( False )
        plugin.dirContextCommitAct.setEnabled( False )
        return

    if pathStatus == plugin.NOT_UNDER_VCS:
        plugin.dirContextInfoAct.setEnabled( False )
        plugin.dirContextUpdateAct.setEnabled( False )
        plugin.dirContextCommitAct.setEnabled( False )

        if path.endswith( os.path.sep ):
            upperDirStatus = plugin.getLocalStatus( os.path.dirname( path[ : -1 ] ) )
        else:
            upperDirStatus = plugin.getLocalStatus( os.path.dirname( path ) )
        if upperDirStatus == plugin.NOT_UNDER_VCS:
            plugin.dirContextAddAct.setEnabled( False )
            plugin.dirContextAddRecursiveAct.setEnabled( False )
        else:
            plugin.dirContextAddAct.setEnabled( upperDirStatus != IND_ERROR )
            plugin.dirContextAddRecursiveAct.setEnabled( upperDirStatus != IND_ERROR )
        return

    plugin.dirContextInfoAct.setEnabled( True )
    plugin.dirContextUpdateAct.setEnabled( True )
    plugin.dirContextAddAct.setEnabled( False )
    plugin.dirContextAddRecursiveAct.setEnabled( True )
    plugin.dirContextCommitAct.setEnabled( True )
    return

def bufferContextMenuAboutToshow( plugin ):
    " Called when the plugin buffer context menu is about to show "
    path = plugin.ide.currentEditorWidget.getFileName()
    if not os.path.isabs( path ):
        plugin.bufContextInfoAct.setEnabled( False )
        plugin.bufContextUpdateAct.setEnabled( False )
        plugin.bufContextAnnotateAct.setEnabled( False )
        plugin.bufContextAddAct.setEnabled( False )
        plugin.bufContextCommitAct.setEnabled( False )
        return

    pathStatus = plugin.getLocalStatus( path )
    if pathStatus == IND_ERROR:
        plugin.bufContextInfoAct.setEnabled( False )
        plugin.bufContextUpdateAct.setEnabled( False )
        plugin.bufContextAnnotateAct.setEnabled( False )
        plugin.bufContextAddAct.setEnabled( False )
        plugin.bufContextCommitAct.setEnabled( False )
        return

    if pathStatus == plugin.NOT_UNDER_VCS:
        plugin.bufContextInfoAct.setEnabled( False )
        plugin.bufContextUpdateAct.setEnabled( False )
        plugin.bufContextAnnotateAct.setEnabled( False )
        plugin.bufContextCommitAct.setEnabled( False )

        upperDirStatus = plugin.getLocalStatus( os.path.dirname( path ) )
        if upperDirStatus == plugin.NOT_UNDER_VCS:
            plugin.bufContextAddAct.setEnabled( False )
        else:
            plugin.bufContextAddAct.setEnabled( upperDirStatus != IND_ERROR )
        return

    plugin.bufContextInfoAct.setEnabled( True )
    plugin.bufContextUpdateAct.setEnabled( True )
    plugin.bufContextAddAct.setEnabled( False )

    widgetType = plugin.ide.currentEditorWidget.getType()
    if widgetType in [ MainWindowTabWidgetBase.PlainTextEditor,
                       MainWindowTabWidgetBase.PythonGraphicsEditor ]:
        plugin.bufContextAnnotateAct.setEnabled( True )
    else:
        plugin.bufContextAnnotateAct.setEnabled( False )

    # Set the Commit... menu item status
    if pathStatus not in [ IND_ADDED, IND_DELETED, IND_MERGED, IND_MODIFIED_LR,
                           IND_MODIFIED_L, IND_REPLACED, IND_CONFLICTED ]:
        plugin.bufContextCommitAct.setEnabled( False )
    else:
        if widgetType in [ MainWindowTabWidgetBase.PlainTextEditor,
                           MainWindowTabWidgetBase.PythonGraphicsEditor ]:
            plugin.bufContextCommitAct.setEnabled(
                            not plugin.ide.currentEditorWidget.isModified() )
        else:
            plugin.bufContextCommitAct.setEnabled( False )
    return
