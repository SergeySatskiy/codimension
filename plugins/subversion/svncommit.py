# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy sergey.satskiy@gmail.com
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

"""Does SVN commit"""

import os.path
import svn
import logging
from .svncommitdlg import SVNPluginCommitDialog
from .svnindicators import (IND_ADDED, IND_DELETED, IND_MERGED,
                            IND_MODIFIED_LR, IND_MODIFIED_L,
                            IND_REPLACED, IND_CONFLICTED, IND_IGNORED)
from ui.qt import (QDialog, QApplication, QCursor, Qt)
from .svnstrconvert import notifyActionToString


COMMIT_ALLOW_STATUSES = [ IND_ADDED, IND_DELETED, IND_MERGED, IND_MODIFIED_LR,
                          IND_MODIFIED_L, IND_REPLACED, IND_CONFLICTED ]
IGNORE_STATUSES = [ IND_IGNORED ]


class SVNCommitMixin:

    def __init__( self ):
        return

    def fileCommit( self ):
        " Called when a file is to be committed "
        path = str( self.fileParentMenu.menuAction().data().toString() )
        self.__svnCommit( path )
        return

    def dirCommit( self ):
        " Called when a directory is to be committed "
        path = str( self.dirParentMenu.menuAction().data().toString() )
        self.__svnCommit( path )
        return

    def bufferCommit( self ):
        " Called when a buffer is to be committed "
        path = self.ide.currentEditorWidget.getFileName()
        self.__svnCommit( path )
        return

    def __svnCommit( self, path ):
        " Called to perform commit "
        client = self.getSVNClient( self.getSettings() )
        doSVNCommit( self, client, path )
        return


def doSVNCommit( plugin, client, path ):
    " Performs SVN commit "

    # The path could be a single file (buffer or project browser) or
    # a directory

    QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
    try:
        if path.endswith( os.path.sep ):
            # This is a directory. Path lists should be built.
            statuses = plugin.getLocalStatus( path, pysvn.depth.infinity )
            if type( statuses ) != list:
                logging.error( "Error checking local SVN statuses for " + path )
                QApplication.restoreOverrideCursor()
                return

            pathsToCommit = []
            pathsToIgnore = []
            for item in statuses:
                if item[ 1 ] in COMMIT_ALLOW_STATUSES:
                    pathsToCommit.append( item )
                elif item[ 1 ] in IGNORE_STATUSES + [ plugin.NOT_UNDER_VCS ]:
                    pathsToIgnore.append( item )

            if not pathsToCommit:
                logging.info( "No paths to commit for " + path )
                QApplication.restoreOverrideCursor()
                return
        else:
            # This is a single file
            status = plugin.getLocalStatus( path )
            if status not in COMMIT_ALLOW_STATUSES:
                logging.error( "Cannot commit " + path +
                               " due to unexpected SVN status" )
                QApplication.restoreOverrideCursor()
                return
            pathsToCommit = [ (path, status), ]
            pathsToIgnore = []
    except Exception as exc:
        logging.error( str( exc ) )
        QApplication.restoreOverrideCursor()
        return
    QApplication.restoreOverrideCursor()


    dlg = SVNPluginCommitDialog( plugin, pathsToCommit, pathsToIgnore )
    res = dlg.exec_()

    if res == QDialog.Accepted:
        if len( dlg.commitPaths ) == 0:
            return
        dlg.commitPaths.sort()

        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        try:
            def getLogMessage( msg = dlg.commitMessage ):
                return True, msg
            def notifyCallback( event ):
                if event[ 'path' ]:
                    action = notifyActionToString( event[ 'action' ] )
                    if action:
                        logging.info( "Commit: " + action + " " + event[ 'path' ] )
                        QApplication.processEvents()
                return

            client.callback_get_log_message = getLogMessage
            client.callback_notify = notifyCallback

            revision = client.checkin( dlg.commitPaths,
                                       log_message = dlg.commitMessage,
                                       recurse = False )
            logging.info( "Committed revision " + str( revision.number ) )
            for path in dlg.commitPaths:
                plugin.notifyPathChanged( path )
        except pysvn.ClientError as exc:
            message = exc.args[ 0 ]
            logging.error( message )
        except Exception as exc:
            logging.error( str( exc ) )
        except:
            logging.error( "Unknown error" )
        QApplication.restoreOverrideCursor()

    return
