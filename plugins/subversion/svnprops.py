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

" Codimension SVN plugin properties functionality implementation "

import os.path, logging
from svnindicators import IND_ERROR
from PyQt4.QtGui import ( QDialog, QTreeWidgetItem, QTreeWidget, QVBoxLayout,
                          QTextEdit, QDialogButtonBox, QLabel, QFontMetrics,
                          QHeaderView, QApplication, QCursor,
                          QHBoxLayout, QToolButton, QGroupBox,
                          QGridLayout, QSizePolicy, QLineEdit )
from PyQt4.QtCore import Qt, SIGNAL, QStringList, QTimer
from ui.itemdelegates import NoOutlineHeightDelegate



class SVNPropsMixin:

    def __init__( self ):
        return

    def fileProps( self ):
        " Called when properties requested for a file via context menu "
        path = str( self.fileParentMenu.menuAction().data().toString() )
        self.__svnProps( path )
        return

    def dirProps( self ):
        " Called when properties  requested for a directory via context menu "
        path = str( self.dirParentMenu.menuAction().data().toString() )
        self.__svnProps( path )
        return

    def bufferProps( self ):
        " Called when properties requested for a buffer "
        path = self.ide.currentEditorWidget.getFileName()
        if not os.path.isabs( path ):
            logging.info( "SVN properties are not applicable for never saved buffer" )
            return
        self.__svnProps( path )
        return

    def __svnProps( self, path ):
        " Implementation of the properties functionality for a path "
        status = self.getLocalStatus( path )
        if status == IND_ERROR:
            logging.error( "Error getting status of " + path )
            return
        if status == self.NOT_UNDER_VCS:
            logging.info( "The " + path + " is not under SVN" )
            return

        client = self.getSVNClient( self.getSettings() )
        dlg = SVNPropsProgress( client, path )

        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        res = dlg.exec_()
        QApplication.restoreOverrideCursor()

        if res == QDialog.Accepted:
            if dlg.properties is None:
                logging.info( "Error getting " + path + " properties" )
                return

            dlg = SVNPluginPropsDialog( self, client, path, dlg.properties )
            dlg.exec_()
        return


class SVNPropsProgress( QDialog ):
    " Minimalistic progress dialog "

    def __init__( self, client, path, parent = None ):
        QDialog.__init__( self, parent )
        self.__cancelRequest = False
        self.__inProcess = False

        self.__client = client
        self.__path = path

        # Transition data
        self.properties = None

        self.__createLayout()
        self.setWindowTitle( "SVN Properties" )
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
        self.__infoLabel = QLabel( "Retrieving properties of '" +
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

    def __process( self ):
        " Update process "
        self.__client.callback_cancel = self.__cancelCallback

        try:
            self.properties = self.__client.proplist( self.__path )
        except Exception, exc:
            logging.error( str( exc ) )
            self.close()
            return
        except:
            logging.error( "Unknown error while retrieving properties of " +
                           self.__path )
            self.close()
            return

        if self.__cancelRequest:
            self.close()
        else:
            self.accept()
        return


class SVNPluginPropsDialog( QDialog ):
    " SVN plugin properties dialog "

    def __init__( self, plugin, client, path, properties, parent = None ):
        QDialog.__init__( self, parent )

        self.__plugin = plugin
        self.__client = client
        self.__path = path
        self.__props = properties

        self.__createLayout()
        self.setWindowTitle( "SVN Properties of " + path )

        for itemPath, itemProps in properties:
            if path == itemPath or path == itemPath + os.path.sep:
                for name, value in itemProps.iteritems():
                    newItem = QTreeWidgetItem(
                        QStringList() << name << value )
                    self.__propsView.addTopLevelItem( newItem )

        self.__resizePropsView()
        self.__sortPropsView()

        self.__propsView.setFocus()
        return

    def __resizePropsView( self ):
        " Resizes the properties table "
        self.__propsView.header().setStretchLastSection( True )
        self.__propsView.header().resizeSections(
                                        QHeaderView.ResizeToContents )
        return

    def __sortPropsView( self ):
        " Sorts the properties table "
        self.__propsView.sortItems(
                    self.__propsView.sortColumn(),
                    self.__propsView.header().sortIndicatorOrder() )
        return

    def __createLayout( self ):
        " Creates the dialog layout "
        self.resize( 640, 480 )
        self.setSizeGripEnabled( True )

        vboxLayout = QVBoxLayout( self )

        hLayout = QHBoxLayout()
        self.__propsView = QTreeWidget()
        self.__propsView.setAlternatingRowColors( True )
        self.__propsView.setRootIsDecorated( False )
        self.__propsView.setItemsExpandable( False )
        self.__propsView.setSortingEnabled( True )
        self.__propsView.setItemDelegate( NoOutlineHeightDelegate( 4 ) )

        propsViewHeader = QTreeWidgetItem(
                QStringList() << "Property Name" << "Property Value" )
        self.__propsView.setHeaderItem( propsViewHeader )
        self.__propsView.header().setSortIndicator( 0, Qt.DescendingOrder )
        hLayout.addWidget( self.__propsView )

        self.__delButton = QToolButton()
        self.__delButton.setText( "Delete" )
        self.__delButton.setFocusPolicy( Qt.NoFocus )
        self.__delButton.setEnabled( False )
        self.connect( self.__delButton, SIGNAL( 'clicked()' ),
                      self.__onDel )
        hLayout.addWidget( self.__delButton, 0, Qt.AlignBottom )
        vboxLayout.addLayout( hLayout )

        # Set property part
        setGroupbox = QGroupBox( self )
        setGroupbox.setTitle( "Set Property" )

        setLayout = QGridLayout( setGroupbox )
        setLayout.addWidget( QLabel( "Name" ), 0, 0, Qt.AlignTop | Qt.AlignRight )
        setLayout.addWidget( QLabel( "Value" ), 1, 0, Qt.AlignTop | Qt.AlignRight )

        self.__nameEdit = QLineEdit()
        self.connect( self.__nameEdit, SIGNAL( 'textChanged(const QString&)' ),
                      self.__nameChanged )
        setLayout.addWidget( self.__nameEdit, 0, 1 )

        self.__valueEdit = QTextEdit()
        self.__valueEdit.setAcceptRichText( False )
        self.connect( self.__valueEdit, SIGNAL( 'textChanged()' ),
                      self.__valueChanged )
        metrics = QFontMetrics( self.__valueEdit.font() )
        rect = metrics.boundingRect( "X" )
        self.__valueEdit.setFixedHeight( rect.height() * 4 + 5 )
        setLayout.addWidget( self.__valueEdit, 1, 1 )

        self.__setButton = QToolButton()
        self.__setButton.setText( "Set" )
        self.__setButton.setFocusPolicy( Qt.NoFocus )
        self.__setButton.setEnabled( False )
        self.connect( self.__setButton, SIGNAL( 'clicked()' ),
                      self.__onSet )
        setLayout.addWidget( self.__setButton, 1, 2, Qt.AlignBottom | Qt.AlignHCenter )
        
        sizePolicy = QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Maximum )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth( setGroupbox.sizePolicy().hasHeightForWidth() )
        setGroupbox.setSizePolicy( sizePolicy )
        vboxLayout.addWidget( setGroupbox )

        # Buttons at the bottom
        buttonBox = QDialogButtonBox( self )
        buttonBox.setOrientation( Qt.Horizontal )
        buttonBox.setStandardButtons( QDialogButtonBox.Ok )
        buttonBox.button( QDialogButtonBox.Ok ).setDefault( True )
        self.connect( buttonBox, SIGNAL( "accepted()" ), self.close )
        vboxLayout.addWidget( buttonBox )
        return

    def __onSet( self ):
        " Triggered when propery set is clicked "
        pass

    def __onDel( self ):
        " Triggered when a property del is clicked "
        pass

    def __nameChanged( self, text ):
        " Triggered when a property name to set is changed "
        self.__updateSetButton()
        return

    def __valueChanged( self ):
        " Triggered when a property value to set is changed "
        self.__updateSetButton()
        return

    def __updateSetButton( self ):
        " Updates the 'Set' button state "
        name = str( self.__nameEdit.text() ).strip()
        value = str( self.__valueEdit.toPlainText() ).strip()
        self.__setButton.setEnabled( name != "" and value != "" )
        return
