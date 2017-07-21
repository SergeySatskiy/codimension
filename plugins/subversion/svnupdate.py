# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Codimension SVN plugin UPDATE command implementation"""

import svn
import logging
import os.path
from ui.qt import (Qt, QTimer, QDialog, QDialogButtonBox, QVBoxLayout, QLabel,
                   QApplication, QCursor)
from .svnstrconvert import notifyActionToString


class SVNUpdateMixin:

    def __init__( self ):
        return

    def fileUpdate( self ):
        " Called when update for a file is requested "
        path = str( self.fileParentMenu.menuAction().data().toString() )
        self.__svnUpdate( path, False )
        return

    def dirUpdate( self ):
        " Called when update for a directory is requested "
        path = str( self.dirParentMenu.menuAction().data().toString() )
        self.__svnUpdate( path, True )
        return

    def bufferUpdate( self ):
        " Called when update for a buffer is requested "
        path = self.ide.currentEditorWidget.getFileName()
        if not os.path.isabs( path ):
            logging.info( "SVN update is not applicable for never saved buffer" )
            return
        self.__svnUpdate( path, False )
        return

    def __svnUpdate( self, path, recursively, rev = None ):
        " Does SVN update "
        client = self.getSVNClient( self.getSettings() )
        if rev is None:
            rev = pysvn.Revision( pysvn.opt_revision_kind.head )
        progressDialog = SVNUpdateProgress( self, client, path, recursively, rev )
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        progressDialog.exec_()
        QApplication.restoreOverrideCursor()
        return



class SVNUpdateProgress( QDialog ):
    " Progress of the svn update command "

    def __init__( self, plugin, client, path, recursively, rev, parent = None ):
        QDialog.__init__( self, parent )
        self.__cancelRequest = False
        self.__inProcess = False

        self.__plugin = plugin
        self.__client = client
        self.__path = path
        self.__recursively = recursively
        self.__rev = rev
        self.__updatedPaths = []

        self.__createLayout()
        self.setWindowTitle( "SVN Update" )
        QTimer.singleShot( 0, self.__process )
        return

    def keyPressEvent( self, event ):
        " Processes the ESC key specifically "
        if event.key() == Qt.Key_Escape:
            self.__cancelRequest = True
            self.__infoLabel.setText( "Cancelling..." )
            QApplication.processEvents()
        return

    def __createLayout( self ):
        " Creates the dialog layout "
        self.resize( 450, 20 )
        self.setSizeGripEnabled( True )

        verticalLayout = QVBoxLayout( self )
        verticalLayout.addWidget( QLabel( "Updating '" + self.__path + "':" ) )
        self.__infoLabel = QLabel( self )
        verticalLayout.addWidget( self.__infoLabel )

        buttonBox = QDialogButtonBox( self )
        buttonBox.setOrientation( Qt.Horizontal )
        buttonBox.setStandardButtons( QDialogButtonBox.Close )
        verticalLayout.addWidget( buttonBox )

        buttonBox.rejected.connect( self.__onClose )
        return

    def __onClose( self ):
        " Triggered when the close button is clicked "
        self.__cancelRequest = True
        self.__infoLabel.setText( "Cancelling..." )
        QApplication.processEvents()
        return

    def closeEvent( self, event ):
        " Window close event handler "
        if self.__inProcess:
            self.__cancelRequest = True
            self.__infoLabel.setText( "Cancelling..." )
            QApplication.processEvents()
            event.ignore()
        else:
            event.accept()
        return

    def __cancelCallback( self ):
        " Called by pysvn regularly "
        QApplication.processEvents()
        return self.__cancelRequest

    def __notifyCallback( self, event ):
        " Called by pysvn. event is a dictionary "
        if 'path' not in event:
            return
        if not event[ 'path' ]:
            return

        message = None
        path = event[ 'path' ]
        if os.path.isdir( path ) and not path.endswith( os.path.sep ):
            path += os.path.sep
        if event[ 'action' ] == pysvn.wc_notify_action.update_completed:
            message = path + " updated to revision " + str( event[ 'revision' ].number )
        elif event[ 'action' ] == pysvn.wc_notify_action.update_started:
            message = "updating " + path + ":"
        else:
            self.__updatedPaths.append( path )
            action = notifyActionToString( event[ 'action' ] )
            if action is not None and action != "unknown":
                message = "  " + action + " " + path
                if event[ 'mime_type' ] == "application/octet-stream":
                    message += " (binary)"

        if message:
            self.__infoLabel.setText( message.strip() )
            logging.info( message )
        QApplication.processEvents()
        return

    def __process( self ):
        " Update process "
        self.__client.callback_cancel = self.__cancelCallback
        self.__client.callback_notify = self.__notifyCallback

        try:
            self.__inProcess = True
            self.__client.update( self.__path, self.__recursively,
                                  self.__rev )
            self.__inProcess = False
        except pysvn.ClientError as exc:
            errorCode = exc.args[ 1 ][ 0 ][ 1 ]
            if errorCode == pysvn.svn_err.cancelled:
                logging.info( "Updating cancelled" )
            else:
                message = exc.args[ 0 ]
                logging.error( message )
            self.__inProcess = False
            self.close()
            return
        except Exception as exc:
            logging.error( str( exc ) )
            self.__inProcess = False
            self.close()
            return
        except:
            logging.error( "Unknown error" )
            self.__inProcess = False
            self.close()
            return

        for updatedPath in self.__updatedPaths:
            self.__plugin.notifyPathChanged( updatedPath )

        if self.__cancelRequest:
            self.close()
        else:
            self.accept()
        return

