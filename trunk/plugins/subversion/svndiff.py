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


class SVNDiffMixin:

    def __init__( self ):
        return

    def fileDiff( self ):
        path = str( self.fileParentMenu.menuAction().data().toString() )
        with open( path ) as f:
            content = f.read()
        self.__svnDiff( path, content, False )
        return

    def bufferDiff( self ):
        editorWidget = self.ide.currentEditorWidget
        path = editorWidget.getFileName()
        content = str( self.ide.currentEditorWidget.getEditor().text() )
        self.__svnDiff( path, content, editorWidget.isModified() )
        return

    def __svnDiff( self, path, content, modified ):
        """ Performs diff for the given content and
            the current version in repository """
        # Get the SVN content first
        client = self.getSVNClient( self.getSettings() )

        try:
            repositoryVersion = client.cat( path )
        except Exception, excpt:
            logging.error( str( excpt ) )
            return

        # Calculate difference
        diff = difflib.unified_diff( content.splitlines(),
                                     repositoryVersion.splitlines() )
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
            source = "--- editing buffer with " + os.path.basename( path )
        else:
            source = "--- local " + os.path.basename( path )
        diffAsText = diffAsText.replace( "--- ", source, 1 )
        diffAsText = diffAsText.replace( "+++ ",
                                         "+++ repository at revision HEAD", 1 )
        self.ide.mainWindow.showDiff( diffAsText,
                                      "SVN diff for " + path )
        return
