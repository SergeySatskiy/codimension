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

import os.path, logging, pysvn
from svnindicators import IND_ERROR
from PyQt4.QtGui import ( QDialog, QTreeWidgetItem, QTreeWidget, QVBoxLayout,
                          QTextEdit, QDialogButtonBox, QLabel, QFontMetrics,
                          QHeaderView, QApplication, QCursor,
                          QHBoxLayout, QToolButton, QGroupBox,
                          QGridLayout, QSizePolicy, QLineEdit, QMessageBox )
from PyQt4.QtCore import Qt
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
        dlg = SVNPluginPropsDialog( self, client, path )
        dlg.exec_()
        return



def readProperties( client, path ):
    " Reads properties of the given path "
    # Properties are always read locally so a progress dialog is not required
    QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
    properties  = None
    try:
        properties = client.proplist( path )
    except pysvn.ClientError as exc:
        message = exc.args[ 0 ]
        logging.error( message )
    except Exception as exc:
        logging.error( str( exc ) )
    except:
        logging.error( "Unknown error while retrieving properties of " + path )
    QApplication.restoreOverrideCursor()
    return properties


class SVNPluginPropsDialog( QDialog ):
    " SVN plugin properties dialog "

    def __init__( self, plugin, client, path, parent = None ):
        QDialog.__init__( self, parent )

        self.__plugin = plugin
        self.__client = client
        self.__path = path

        self.__createLayout()
        self.setWindowTitle( "SVN Properties of " + path )
        self.__populate()
        self.__propsView.setFocus()
        return

    def __populate( self ):
        " Populate the properties list "
        # Get the currently selected name
        selectedName = None
        selected = list( self.__propsView.selectedItems() )
        if selected:
            selectedName = str( selected[ 0 ].text( 0 ) )

        self.__propsView.clear()
        properties = readProperties( self.__client, self.__path )
        if properties:
            for itemPath, itemProps in properties:
                if self.__path == itemPath or \
                   self.__path == itemPath + os.path.sep:
                    for name, value in itemProps.iteritems():
                        name = str( name ).strip()
                        value = str( value ).strip()
                        newItem = QTreeWidgetItem( [ name, value ] )
                        self.__propsView.addTopLevelItem( newItem )

        self.__resizePropsView()
        self.__sortPropsView()

        if selectedName:
            index = 0
            for index in range( 0, self.__propsView.topLevelItemCount() ):
                item = self.__propsView.topLevelItem( index )
                if selectedName == item.text( 0 ):
                    item.setSelected( True )
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
        self.__propsView.itemSelectionChanged.connect( self.__propsSelectionChanged )

        propsViewHeader = QTreeWidgetItem( [ "Property Name", "Property Value" ] )
        self.__propsView.setHeaderItem( propsViewHeader )
        self.__propsView.header().setSortIndicator( 0, Qt.DescendingOrder )
        hLayout.addWidget( self.__propsView )

        self.__delButton = QToolButton()
        self.__delButton.setText( "Delete" )
        self.__delButton.setFocusPolicy( Qt.NoFocus )
        self.__delButton.setEnabled( False )
        self.__delButton.clicked.connect( self.__onDel )
        hLayout.addWidget( self.__delButton, 0, Qt.AlignBottom )
        vboxLayout.addLayout( hLayout )

        # Set property part
        setGroupbox = QGroupBox( self )
        setGroupbox.setTitle( "Set Property" )

        setLayout = QGridLayout( setGroupbox )
        setLayout.addWidget( QLabel( "Name" ), 0, 0, Qt.AlignTop | Qt.AlignRight )
        setLayout.addWidget( QLabel( "Value" ), 1, 0, Qt.AlignTop | Qt.AlignRight )

        self.__nameEdit = QLineEdit()
        self.__nameEdit.textChanged.connect( self.__nameChanged )
        setLayout.addWidget( self.__nameEdit, 0, 1 )

        self.__valueEdit = QTextEdit()
        self.__valueEdit.setAcceptRichText( False )
        self.__valueEdit.textChanged.connect( self.__valueChanged )
        metrics = QFontMetrics( self.__valueEdit.font() )
        rect = metrics.boundingRect( "X" )
        self.__valueEdit.setFixedHeight( rect.height() * 4 + 5 )
        setLayout.addWidget( self.__valueEdit, 1, 1 )

        self.__setButton = QToolButton()
        self.__setButton.setText( "Set" )
        self.__setButton.setFocusPolicy( Qt.NoFocus )
        self.__setButton.setEnabled( False )
        self.__setButton.clicked.connect( self.__onSet )
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
        buttonBox.accepted.connect( self.close )
        vboxLayout.addWidget( buttonBox )
        return

    def __onSet( self ):
        " Triggered when propery set is clicked "
        name = self.__nameEdit.text().strip()
        value = self.__valueEdit.toPlainText().strip()
        try:
            commitInfo = self.__client.propset( name, value, self.__path )
            if commitInfo:
                logging.info( str( commitInfo ) )
            self.__populate()
            self.__plugin.notifyPathChanged( self.__path )
            self.__nameEdit.clear()
            self.__valueEdit.clear()
            self.__propsView.setFocus()
        except pysvn.ClientError as exc:
            message = exc.args[ 0 ]
            logging.error( message )
            return
        except Exception as exc:
            logging.error( str( exc ) )
            return
        except:
            logging.error( "Unknown property setting error" )
            return

    def __propsSelectionChanged( self ):
        " Selection of a property has changed "
        selected = list( self.__propsView.selectedItems() )
        self.__delButton.setEnabled( len( selected ) > 0 )
        return

    def __onDel( self ):
        " Triggered when a property del is clicked "
        selected = list( self.__propsView.selectedItems() )
        if len( selected ) == 0:
            self.__delButton.setEnabled( False )
            return

        name = str( selected[ 0 ].text( 0 ) )
        res = QMessageBox.warning( self, "Deleting Property",
                    "You are about to delete <b>" + name +
                    "</b> SVN property from " + self.__path + ".\nAre you sure?",
                           QMessageBox.StandardButtons(
                                QMessageBox.Cancel | QMessageBox.Yes ),
                           QMessageBox.Cancel )
        if res != QMessageBox.Yes:
            return

        try:
            self.__client.propdel( name, self.__path )
            self.__populate()
            self.__plugin.notifyPathChanged( self.__path )
            self.__propsView.setFocus()
        except pysvn.ClientError as exc:
            message = exc.args[ 0 ]
            logging.error( message )
            return
        except Exception as exc:
            logging.error( str( exc ) )
            return
        except:
            logging.error( "Unknown property deleting error" )
            return

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
        name = self.__nameEdit.text().strip()
        value = self.__valueEdit.toPlainText().strip()
        self.__setButton.setEnabled( name != "" and value != "" )
        return
