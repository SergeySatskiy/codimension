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

" Codimension SVN plugin UPDATE command implementation "

import pysvn
import logging
from PyQt4.QtCore import Qt, SIGNAL, QTimer
from PyQt4.QtGui import ( QDialog, QDialogButtonBox, QVBoxLayout, QLabel,
                          QApplication, QCursor )

from svnstrconvert import notifyActionToString



def doSVNUpdate( client, path, recursively, rev = None ):
    " Performs the SVN Update for the given path "

    if rev is None:
        rev = pysvn.Revision( pysvn.opt_revision_kind.head )
    progressDialog = SVNUpdateProgress( client, path, recursively, rev )
    QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
    progressDialog.exec_()
    QApplication.restoreOverrideCursor()
    return


class SVNUpdateProgress( QDialog ):
    " Progress of the svn update command "

    def __init__( self, client, path, recursively, rev, parent = None ):
        QDialog.__init__( self )
        self.__cancelRequest = False
        self.__inProcess = False

        self.__client = client
        self.__path = path
        self.__recursively = recursively
        self.__rev = rev

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

        self.connect( buttonBox, SIGNAL( "rejected()" ), self.__onClose )
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
        message = None
        if event[ 'action' ] == pysvn.wc_notify_action.update_completed:
            message = "Updated to revision " + str( event[ 'revision' ].number )
        elif event[ 'action' ] == pysvn.wc_notify_action.update_started:
            message = "Updating '" + event[ 'path' ] + "':"
        elif event[ 'path' ]:
            action = notifyActionToString( event[ 'action' ] )
            if action is not None and action != "unknown":
                message = action + " " + event[ 'path' ]
                if event[ 'mime_type' ] == "application/octet-stream":
                    message += " (binary)"

        if message:
            self.__infoLabel.setText( message )
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
        except pysvn.ClientError, exc:
            errorCode = exc.args[ 1 ][ 0 ][ 1 ]
            if errorCode == pysvn.svn_err.cancelled:
                logging.info( "Updating cancelled" )
            else:
                message = exc.args[ 0 ]
                logging.error( message )
            self.__inProcess = False
            self.close()
            return
        except Exception, exc:
            logging.error( str( exc ) )
            self.__inProcess = False
            self.close()
            return
        except:
            logging.error( "Unknown error" )
            self.__inProcess = False
            self.close()
            return

        if self.__cancelRequest:
            self.close()
        else:
            self.accept()
        return

