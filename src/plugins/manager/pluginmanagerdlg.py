#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2013  Sergey Satskiy <sergey.satskiy@gmail.com>
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

""" Plugins manager dialog """

from PyQt4.QtCore import Qt, SIGNAL
from PyQt4.QtGui import ( QDialog, QTreeWidgetItem, QTreeWidget, QVBoxLayout,
                          QTextEdit, QDialogButtonBox )
from itemdelegates import NoOutlineHeightDelegate


class PluginItem( QTreeWidgetItem ):
    " Single plugin item "

    def __init__( self, cdmPligin ):
        return



class PluginsDialog( QDialog ):
    " Codimension plugins dialog "

    def __init__( self, pluginManager, parent = None ):
        QDialog.__init__( self, parent )
        self.__pluginManager = pluginManager
        self.__createLayout()
        self.__populate()
        return

    def __createLayout( self ):
        " Creates the dialog layout "

        layout = QVBoxLayout()
        layout.setContentsMargins( 1, 1, 1, 1 )

        # Plugins list
        self.__pluginsView = QTreeWidget()
        self.__pluginsView.setAlternatingRowColors( True )
        self.__pluginsView.setRootIsDecorated( False )
        self.__pluginsView.setItemsExpandable( False )
        self.__pluginsView.setSortingEnabled( True )
        self.__pluginsView.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        self.__pluginsView.setUniformRowHeights( True )

        self.__pluginsHeader = QTreeWidgetItem(
                QStringList() << "Alert" << "System/user" << "Enable" << "Name" << "Version" )
        self.__pluginsView.setHeaderItem( self.__pluginsHeader )
        self.__pluginsHeader.header().setSortIndicator( 2, Qt.AscendingOrder )

        layout.addWidget( self.__pluginsView )

        # Detailed information
        detailsLabel = QLabel( "Detailed information" )
        layout.addWidget( detailsLabel )
        self.__detailsText = QTextEdit()
        self.__detailsText.setReadOnly( True )
        self.__detailsText.setAcceptRichText( False )
        layout.addWidget( self.__detailsText )

        # Errors/warnings
        errorsLabel = QLabel( "Errors / warnings" )
        layout.addWidget( errorsLabel )
        self.__errorsText = QTextEdit()
        self.__errorsText.setReadOnly( True )
        self.__errorsText.setAcceptRichText( False )
        layout.addWidget( self.__errorsText )

        # Buttons box
        buttonBox = QDialogButtonBox( self )
        buttonBox.setOrientation( Qt.Horizontal )
        buttonBox.setStandardButtons( QDialogButtonBox.Ok )
        self.__OKButton = buttonBox.button( QDialogButtonBox.Ok )
        self.__OKButton.setDefault( True )
        self.connect( buttonBox, SIGNAL( "accepted()" ), self.close )
        self.connect( buttonBox, SIGNAL( "rejected()" ), self.close )
        layout.addWidget( buttonBox )

        self.setLayout( layout )
        return


