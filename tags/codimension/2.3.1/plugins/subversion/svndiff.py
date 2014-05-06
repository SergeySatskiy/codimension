#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy sergey.satskiy@gmail.com
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

" SVN diff functionality "

import logging
import difflib
import os.path
import pysvn
from PyQt4.QtGui import QApplication, QCursor
from PyQt4.QtCore import Qt
from svnindicators import IND_UPTODATE


def getLocalRevisionNumber( client, path ):
    " Provides the local revision number "
    info = client.info2( path, recurse = False )
    return int( info[ 0 ][ 1 ][ "rev" ].number )


def getReposRevisionNumber( client, path ):
    " Provides the repository revision number "
    log  = client.log( path,
               revision_start = pysvn.Revision( pysvn.opt_revision_kind.head ),
               limit = 1 )
    if log:
        return int( log[ 0 ][ "revision" ].number )
    return None



class SVNDiffMixin:

    def __init__( self ):
        return

    def fileDiff( self ):
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        path = str( self.fileParentMenu.menuAction().data().toString() )
        with open( path ) as f:
            content = f.read()
        self.__svnDiff( path, content, False )
        QApplication.restoreOverrideCursor()
        return

    def bufferDiff( self ):
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        editorWidget = self.ide.currentEditorWidget
        path = editorWidget.getFileName()
        content = str( self.ide.currentEditorWidget.getEditor().text() )
        self.__svnDiff( path, content, editorWidget.isModified() )
        QApplication.restoreOverrideCursor()
        return

    def __svnDiff( self, path, content, modified ):
        """ Performs diff for the given content and
            the current version in repository """
        # Get the SVN content first
        client = self.getSVNClient( self.getSettings() )

        try:
            localStatus = self.getLocalStatus( path )
            localRevisionNumber = getLocalRevisionNumber( client, path )
            reposRevisionNumber = getReposRevisionNumber( client, path )

            if reposRevisionNumber is None:
                logging.info( "The path " + path +
                              " does not exist in repository" )
                return

            localAtLeft = False
            if localStatus == IND_UPTODATE:
                if localRevisionNumber < reposRevisionNumber:
                    localAtLeft = True

            repositoryVersion = client.cat( path )

            # Calculate difference
            if localAtLeft:
                diff = difflib.unified_diff( content.splitlines(),
                                             repositoryVersion.splitlines(),
                                             n = 5 )
            else:
                diff = difflib.unified_diff( repositoryVersion.splitlines(),
                                             content.splitlines(), n = 5 )
            nodiffMessage = path + " has no difference to the " \
                                   "repository at revision HEAD"
            if modified:
                nodiffMessage = "Editing buffer with " + nodiffMessage
            if diff is None:
                logging.info( nodiffMessage )
                return

            # There are changes, so replace the text and tell about the changes
            diffAsText = '\n'.join( list( diff ) )
            if diffAsText.strip() == '':
                logging.info( nodiffMessage )
                return

            if modified:
                localSpec = "editing buffer with " + \
                            os.path.basename( path ) + " based on rev." + \
                            str( localRevisionNumber )
            else:
                localSpec = "local " + os.path.basename( path ) + \
                            " (rev." + str( localRevisionNumber ) + ")"
            reposSpec = "repository at revision HEAD (rev." + \
                        str( reposRevisionNumber ) + ")"
            if localAtLeft:
                diffAsText = diffAsText.replace( "--- ", "--- " + localSpec, 1 )
                diffAsText = diffAsText.replace( "+++ ", "+++ " + reposSpec, 1 )
            else:
                diffAsText = diffAsText.replace( "+++ ", "+++ " + localSpec, 1 )
                diffAsText = diffAsText.replace( "--- ", "--- " + reposSpec, 1 )
        except Exception, excpt:
            logging.error( str( excpt ) )
            return

        self.ide.mainWindow.showDiff( diffAsText,
                                      "SVN diff for " + path )
        return
