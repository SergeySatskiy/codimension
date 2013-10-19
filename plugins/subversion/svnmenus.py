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
                            IND_REPLACED, IND_CONFLICTED, IND_UPTODATE )
from ui.mainwindowtabwidgetbase import MainWindowTabWidgetBase


class SVNMenuMixin:
    " Adds menu functionality to the plugin class "

    def __init__( self ):
        return

    def populateMainMenu( self, parentMenu ):
        " Called to build main menu "
        self.connect( parentMenu, SIGNAL( "aboutToShow()" ),
                      self.onMainMenuAboutToShow )
        parentMenu.addAction( "Configure", self.configure )
        return

    def populateFileContextMenu( self, parentMenu ):
        " Called to build a file context menu in the project and FS browsers "
        self.fileParentMenu = parentMenu
        self.connect( parentMenu, SIGNAL( "aboutToShow()" ),
                      self.onFileContextMenuAboutToShow )
        self.fileContextInfoAct = parentMenu.addAction( "&Info", self.fileInfo )
        self.fileContextAnnotateAct = parentMenu.addAction( "&Annotate", self.fileAnnotate )
        self.fileContextDiffAct = parentMenu.addAction( "&Diff", self.fileDiff )
        parentMenu.addSeparator()
        self.fileContextUpdateAct = parentMenu.addAction( "&Update", self.fileUpdate )
        self.fileContextAddAct = parentMenu.addAction( "A&dd", self.fileAddToRepository )
        self.fileContextCommitAct = parentMenu.addAction( "&Commit...", self.fileCommit )
        self.fileContextRevertAct = parentMenu.addAction( "&Revert", self.fileRevert )
        parentMenu.addSeparator()
        self.fileContextDeleteAct = parentMenu.addAction( "D&elete...", self.fileDelete )
        return

    def populateDirectoryContextMenu( self, parentMenu ):
        " Called to build a dir context menu in the project and FS browsers "
        self.dirParentMenu = parentMenu
        self.connect( parentMenu, SIGNAL( "aboutToShow()" ),
                      self.onDirectoryContextMenuAboutToShow )
        self.dirContextInfoAct = parentMenu.addAction( "&Info", self.dirInfo )
        self.dirContextLocalStatusAct = parentMenu.addAction( "&Status (local only)", self.dirLocalStatus )
        self.dirContextReposStatusAct = parentMenu.addAction( "S&tatus (repository)", self.dirRepositoryStatus )
        parentMenu.addSeparator()
        self.dirContextUpdateAct = parentMenu.addAction( "&Update", self.dirUpdate )
        self.dirContextAddAct = parentMenu.addAction( "A&dd", self.dirAddToRepository )
        self.dirContextAddRecursiveAct = parentMenu.addAction( "Add recursively", self.dirAddToRepositoryRecursively )
        self.dirContextCommitAct = parentMenu.addAction( "&Commit...", self.dirCommit )
        self.dirContextRevertAct = parentMenu.addAction( "&Revert", self.dirRevert )
        parentMenu.addSeparator()
        self.dirContextDeleteAct = parentMenu.addAction( "D&elete...", self.dirDelete )
        return

    def populateBufferContextMenu( self, parentMenu ):
        " Called to build a buffer context menu "
        self.connect( parentMenu, SIGNAL( "aboutToShow()" ),
                      self.onBufferContextMenuAboutToshow )
        self.bufContextInfoAct = parentMenu.addAction( "&Info", self.bufferInfo )
        self.bufContextAnnotateAct = parentMenu.addAction( "&Annotate", self.bufferAnnotate )
        self.bufContextUpdateAct = parentMenu.addAction( "&Update", self.bufferUpdate )
        self.bufContextDiffAct = parentMenu.addAction( "&Diff", self.bufferDiff )
        parentMenu.addSeparator()
        self.bufContextAddAct = parentMenu.addAction( "A&dd", self.bufferAddToRepository )
        self.bufContextCommitAct = parentMenu.addAction( "&Commit...", self.bufferCommit )
        self.bufContextRevertAct = parentMenu.addAction( "&Revert", self.bufferRevert )
        parentMenu.addSeparator()
        self.bufContextDeleteAct = parentMenu.addAction( "D&elete...", self.bufferDelete )
        return

    def onMainMenuAboutToShow( self ):
        " Called when a main menu is about to show "
        return

    def onFileContextMenuAboutToShow( self ):
        " Called when the plugin file context menu is about to show "
        path = str( self.fileParentMenu.menuAction().data().toString() )
        pathStatus = self.getLocalStatus( path )
        if pathStatus == IND_ERROR:
            self.fileContextInfoAct.setEnabled( False )
            self.fileContextUpdateAct.setEnabled( False )
            self.fileContextAnnotateAct.setEnabled( False )
            self.fileContextAddAct.setEnabled( False )
            self.fileContextCommitAct.setEnabled( False )
            self.fileContextDeleteAct.setEnabled( False )
            self.fileContextRevertAct.setEnabled( False )
            self.fileContextDiffAct.setEnabled( False )
            return

        if pathStatus == self.NOT_UNDER_VCS:
            self.fileContextInfoAct.setEnabled( False )
            self.fileContextUpdateAct.setEnabled( False )
            self.fileContextAnnotateAct.setEnabled( False )
            self.fileContextCommitAct.setEnabled( False )
            self.fileContextDeleteAct.setEnabled( False )
            self.fileContextRevertAct.setEnabled( False )
            self.fileContextDiffAct.setEnabled( False )

            upperDirStatus = self.getLocalStatus( os.path.dirname( path ) )
            if upperDirStatus == self.NOT_UNDER_VCS:
                self.fileContextAddAct.setEnabled( False )
            else:
                self.fileContextAddAct.setEnabled( upperDirStatus != IND_ERROR )
            return

        self.fileContextInfoAct.setEnabled( True )
        self.fileContextUpdateAct.setEnabled( True )
        self.fileContextAnnotateAct.setEnabled( True )
        self.fileContextAddAct.setEnabled( False )
        self.fileContextCommitAct.setEnabled( pathStatus in [
                        IND_ADDED, IND_DELETED, IND_MERGED, IND_MODIFIED_LR,
                        IND_MODIFIED_L, IND_REPLACED, IND_CONFLICTED ] )
        self.fileContextDeleteAct.setEnabled( pathStatus != IND_DELETED )
        self.fileContextRevertAct.setEnabled( pathStatus != IND_UPTODATE )
        self.fileContextDiffAct.setEnabled( True )
        return

    def onDirectoryContextMenuAboutToShow( self ):
        " Called when the plugin directory context manu is about to show "
        path = str( self.dirParentMenu.menuAction().data().toString() )
        pathStatus = self.getLocalStatus( path )
        if pathStatus == IND_ERROR:
            self.dirContextInfoAct.setEnabled( False )
            self.dirContextUpdateAct.setEnabled( False )
            self.dirContextAddAct.setEnabled( False )
            self.dirContextAddRecursiveAct.setEnabled( False )
            self.dirContextCommitAct.setEnabled( False )
            self.dirContextLocalStatusAct.setEnabled( False )
            self.dirContextReposStatusAct.setEnabled( False )
            self.dirContextDeleteAct.setEnabled( False )
            self.dirContextRevertAct.setEnabled( False )
            return

        if pathStatus == self.NOT_UNDER_VCS:
            self.dirContextInfoAct.setEnabled( False )
            self.dirContextUpdateAct.setEnabled( False )
            self.dirContextCommitAct.setEnabled( False )
            self.dirContextLocalStatusAct.setEnabled( False )
            self.dirContextReposStatusAct.setEnabled( False )
            self.dirContextDeleteAct.setEnabled( False )
            self.dirContextRevertAct.setEnabled( False )

            if path.endswith( os.path.sep ):
                upperDirStatus = self.getLocalStatus( os.path.dirname( path[ : -1 ] ) )
            else:
                upperDirStatus = self.getLocalStatus( os.path.dirname( path ) )
            if upperDirStatus == self.NOT_UNDER_VCS:
                self.dirContextAddAct.setEnabled( False )
                self.dirContextAddRecursiveAct.setEnabled( False )
            else:
                self.dirContextAddAct.setEnabled( upperDirStatus != IND_ERROR )
                self.dirContextAddRecursiveAct.setEnabled( upperDirStatus != IND_ERROR )
            return

        self.dirContextInfoAct.setEnabled( True )
        self.dirContextUpdateAct.setEnabled( True )
        self.dirContextAddAct.setEnabled( False )
        self.dirContextAddRecursiveAct.setEnabled( True )
        self.dirContextCommitAct.setEnabled( True )
        self.dirContextLocalStatusAct.setEnabled( True )
        self.dirContextReposStatusAct.setEnabled( True )
        self.dirContextDeleteAct.setEnabled( pathStatus != IND_DELETED )
        self.dirContextRevertAct.setEnabled( pathStatus != IND_UPTODATE )
        return

    def onBufferContextMenuAboutToshow( self ):
        " Called when the plugin buffer context menu is about to show "
        path = self.ide.currentEditorWidget.getFileName()
        if not os.path.isabs( path ):
            self.bufContextInfoAct.setEnabled( False )
            self.bufContextUpdateAct.setEnabled( False )
            self.bufContextAnnotateAct.setEnabled( False )
            self.bufContextAddAct.setEnabled( False )
            self.bufContextCommitAct.setEnabled( False )
            self.bufContextDeleteAct.setEnabled( False )
            self.bufContextRevertAct.setEnabled( False )
            self.bufContextDiffAct.setEnabled( False )
            return

        pathStatus = self.getLocalStatus( path )
        if pathStatus == IND_ERROR:
            self.bufContextInfoAct.setEnabled( False )
            self.bufContextUpdateAct.setEnabled( False )
            self.bufContextAnnotateAct.setEnabled( False )
            self.bufContextAddAct.setEnabled( False )
            self.bufContextCommitAct.setEnabled( False )
            self.bufContextDeleteAct.setEnabled( False )
            self.bufContextRevertAct.setEnabled( False )
            self.bufContextDiffAct.setEnabled( False )
            return

        if pathStatus == self.NOT_UNDER_VCS:
            self.bufContextInfoAct.setEnabled( False )
            self.bufContextUpdateAct.setEnabled( False )
            self.bufContextAnnotateAct.setEnabled( False )
            self.bufContextCommitAct.setEnabled( False )
            self.bufContextDeleteAct.setEnabled( False )
            self.bufContextRevertAct.setEnabled( False )
            self.bufContextDiffAct.setEnabled( False )

            upperDirStatus = self.getLocalStatus( os.path.dirname( path ) )
            if upperDirStatus == self.NOT_UNDER_VCS:
                self.bufContextAddAct.setEnabled( False )
            else:
                self.bufContextAddAct.setEnabled( upperDirStatus != IND_ERROR )
            return

        self.bufContextInfoAct.setEnabled( True )
        self.bufContextUpdateAct.setEnabled( True )
        self.bufContextAddAct.setEnabled( False )
        self.bufContextDeleteAct.setEnabled( pathStatus != IND_DELETED )
        self.bufContextRevertAct.setEnabled( pathStatus != IND_UPTODATE )
        self.bufContextDiffAct.setEnabled( True )

        widgetType = self.ide.currentEditorWidget.getType()
        if widgetType in [ MainWindowTabWidgetBase.PlainTextEditor,
                           MainWindowTabWidgetBase.PythonGraphicsEditor ]:
            self.bufContextAnnotateAct.setEnabled( True )
        else:
            self.bufContextAnnotateAct.setEnabled( False )

        # Set the Commit... menu item status
        if pathStatus not in [ IND_ADDED, IND_DELETED, IND_MERGED, IND_MODIFIED_LR,
                               IND_MODIFIED_L, IND_REPLACED, IND_CONFLICTED ]:
            self.bufContextCommitAct.setEnabled( False )
        else:
            if widgetType in [ MainWindowTabWidgetBase.PlainTextEditor,
                               MainWindowTabWidgetBase.PythonGraphicsEditor ]:
                self.bufContextCommitAct.setEnabled(
                                not self.ide.currentEditorWidget.isModified() )
            else:
                self.bufContextCommitAct.setEnabled( False )
        return
