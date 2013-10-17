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

" SVN Status functionality "

import os.path
import pysvn
import logging
from svnindicators import IND_ERROR
from PyQt4.QtCore import Qt, QTimer, SIGNAL
from PyQt4.QtGui import ( QDialog, QApplication, QVBoxLayout, QLabel,
                          QDialogButtonBox, QCursor )
from svnstrconvert import notifyActionToString



class SVNStatusMixin:

    def __init__( self ):
        return

    def dirLocalStatus( self ):
        " Called when a local status is requested for a directory "
        path = str( self.dirParentMenu.menuAction().data().toString() )
        self.__svnStatus( path, False )
        return

    def dirRepositoryStatus( self ):
        " Called when a repository status is requested for a directory "
        path = str( self.dirParentMenu.menuAction().data().toString() )
        self.__svnStatus( path, True )
        return

    def __svnStatus( self, path, update ):
        " Called to perform svn status "
        settings = self.getSettings()
        client = self.getSVNClient( settings )

        dlg = SVNStatusProgress( self, client, path, update )
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        res = dlg.exec_()
        QApplication.restoreOverrideCursor()

        if res != QDialog.Accepted:
            logging.info( "SVN status for '" + path + "' cancelled" )
            return

        if len( dlg.statusList ) == 0:
            logging.error( "Error getting SVN status for '" + path + "'" )
            return

        print dlg.statusList

        return




class SVNStatusProgress( QDialog ):
    " Minimalistic progress dialog "

    def __init__( self, plugin, client, path, update, parent = None ):
        QDialog.__init__( self, parent )
        self.__cancelRequest = False
        self.__inProcess = False

        self.__plugin = plugin
        self.__client = client
        self.__path = path
        self.__update = update

        # Transition data
        self.statusList = None

        self.__createLayout()
        self.setWindowTitle( "SVN Status" )
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
        self.__infoLabel = QLabel( "Getting status of '" +
                                   self.__path + "'..." )
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
            statusList = self.__client.status( self.__path,
                                               update = self.__update,
                                               depth = pysvn.depth.infinity )
            if not statusList:
                # Try again, may be it is because the depth
                statusList = self.__client.status( self.__path,
                                                   update = self.__update,
                                                   depth = pysvn.depth.empty )

            self.statusList = []
            for status in statusList:
                reportPath = status.path
                if not status.path.endswith( os.path.sep ):
                    if status.entry is None:
                        if os.path.isdir( status.path ):
                            reportPath += os.path.sep
                    elif status.entry.kind == pysvn.node_kind.dir:
                        reportPath += os.path.sep

                self.statusList.append( (reportPath,
                                         self.__plugin.convertSVNStatus( status ),
                                         None) )
        except pysvn.ClientError, exc:
            errorCode = exc.args[ 1 ][ 0 ][ 1 ]
            if errorCode == pysvn.svn_err.wc_not_working_copy:
                self.statusList = [ (self.__path, self.NOT_UNDER_VCS, None), ]
            else:
                message = exc.args[ 0 ]
                self.statusList = [ (self.__path, IND_ERROR, message), ]
        except Exception, exc:
            self.statusList = [ (self.__path, IND_ERROR,
                                 "Error: " + str( exc )), ]
        except:
            self.statusList = [ (self.__path, IND_ERROR, "Unknown error"), ]

        if self.__cancelRequest:
            self.close()
        else:
            self.accept()
        return
