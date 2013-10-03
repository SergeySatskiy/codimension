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

" Codimension SVN plugin ANNOTATE command implementation "

import pysvn
import logging
from copy import deepcopy
from PyQt4.QtCore import Qt, SIGNAL, QTimer
from PyQt4.QtGui import ( QDialog, QDialogButtonBox, QVBoxLayout, QLabel,
                          QApplication, QCursor )

from svnstrconvert import notifyActionToString



def doSVNAnnotate( client, path,
                   revStart = None, revEnd = None, revPeg = None ):
    " Performs the SVN annotate for the given path "
    if revStart is None:
        revStart = pysvn.Revision( pysvn.opt_revision_kind.number, 0 )
    if revEnd is None:
        revEnd = pysvn.Revision( pysvn.opt_revision_kind.head )
    if revPeg is None:
        revPeg = pysvn.Revision( pysvn.opt_revision_kind.unspecified )

    progressDialog = SVNAnnotateProgress( client, path,
                                          revStart, revEnd, revPeg )
    QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
    res = progressDialog.exec_()
    QApplication.restoreOverrideCursor()

    if res == QDialog.Accepted:
        fullText = "\n".join( [ lineInfo[ 'line' ]
                                for lineInfo in progressDialog.annotation ] )

        revisions = deepcopy( progressDialog.revisionsInfo.keys() )
        revisionPerLine = []
        for lineInfo in progressDialog.annotation:
            revNumber = lineInfo[ 'revision' ].number
            revisionPerLine.append( revNumber )
            if revNumber in revisions:
                progressDialog.revisionsInfo[ revNumber ][ 'date' ] = lineInfo[ 'date' ]
                progressDialog.revisionsInfo[ revNumber ][ 'author' ] = lineInfo[ 'author' ]
                revisions.remove( revNumber )

        return fullText, revisionPerLine, progressDialog.revisionsInfo

    return None, None, None


class SVNAnnotateProgress( QDialog ):
    " Minimalistic progress dialog "

    def __init__( self, client, path, revStart, revEnd, revPeg, parent = None ):
        QDialog.__init__( self, parent )
        self.__cancelRequest = False
        self.__inProcess = False

        self.__client = client
        self.__path = path
        self.__revStart = revStart
        self.__revEnd = revEnd
        self.__revPeg = revPeg

        # Transition data
        self.annotation = None
        self.revisionsInfo = None

        self.__createLayout()
        self.setWindowTitle( "SVN Annotate" )
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
        self.__infoLabel = QLabel( "Annotating '" + self.__path + "'..." )
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
        if event[ 'path' ]:
            action = notifyActionToString( event[ 'action' ] )
            if action is not None and action != "unknown":
                message = action + " " + event[ 'path' ]
                if event[ 'mime_type' ] == "application/octet-stream":
                    message += " (binary)"

        if message:
            self.__infoLabel.setText( message )
        QApplication.processEvents()
        return

    def __process( self ):
        " Update process "
        self.__client.callback_cancel = self.__cancelCallback
        self.__client.callback_notify = self.__notifyCallback

        try:
            self.__inProcess = True
            self.annotation = self.__client.annotate( self.__path,
                                                      self.__revStart,
                                                      self.__revEnd,
                                                      self.__revPeg )
            self.__collectRevisionInfo()
            self.__inProcess = False
        except pysvn.ClientError, exc:
            errorCode = exc.args[ 1 ][ 0 ][ 1 ]
            if errorCode == pysvn.svn_err.cancelled:
                logging.info( "Annotating of '" + self.__path + "' cancelled" )
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

    def __collectRevisionInfo( self ):
        " Collects information about revision messages "
        self.__infoLabel.setText( "Collecting revision messages..." )
        QApplication.processEvents()
        revisions = set()
        for item in self.annotation:
            if item[ 'revision' ].kind == pysvn.opt_revision_kind.number:
                revisions.add( item[ 'revision' ].number )

        self.revisionsInfo = {}
        itemNumber = 1
        total = str( len( revisions ) )
        for revision in revisions:
            self.__infoLabel.setText( "Getting message for revision " +
                                      str( revision ) + " (" +
                                      str( itemNumber ) + " out of " +
                                      total + ")" )
            QApplication.processEvents()
            if self.__cancelRequest:
                break

            rev = pysvn.Revision( pysvn.opt_revision_kind.number, revision )
            logMessage = self.__client.log( self.__path,
                                            revision_start = rev,
                                            limit = 1 )
            self.revisionsInfo[ revision ] = { 'message' :
                                                    logMessage[ 0 ].message }
            itemNumber += 1
        return
