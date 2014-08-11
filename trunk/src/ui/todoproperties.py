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

#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#


""" todo and fixme properties dialog """


from PyQt4.QtCore import Qt, QMetaObject
from PyQt4.QtGui import ( QDialog, QLineEdit, QGridLayout, QLabel, QSizePolicy,
                          QDialogButtonBox, QCheckBox )


class TodoPropertiesDialog( QDialog ):
    """ todo properties dialog implementation """

    def __init__( self, todo = None, parent = None ):

        QDialog.__init__( self, parent )
        self.setWindowTitle( "Todo Properties" )

        self.__createLayout()

        if todo is not None:
            self.descriptionEdit.setText( todo.description )
            self.completedCheckBox.setChecked( todo.completed )
            self.filenameEdit.setText( todo.filename )
            if todo.lineno:
                self.linenoEdit.setText( str( todo.lineno ) )
        return

    def __createLayout( self ):
        """ Creates the dialog layout """

        self.resize( 579, 297 )
        self.setSizeGripEnabled( True )

        self.gridlayout = QGridLayout( self )

        self.descriptionLabel = QLabel( self )
        self.descriptionLabel.setText( "Description:" )
        self.gridlayout.addWidget( self.descriptionLabel, 0, 0, 1, 1 )

        self.descriptionEdit = QLineEdit( self )
        self.gridlayout.addWidget( self.descriptionEdit, 0, 1, 1, 3 )

        sizePolicy = QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Preferred )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )

        self.completedCheckBox = QCheckBox( self )
        self.completedCheckBox.setText( "Completed" )
        sizePolicy = QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Fixed )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth( self.completedCheckBox.sizePolicy().hasHeightForWidth() )
        self.completedCheckBox.setSizePolicy( sizePolicy )
        self.gridlayout.addWidget( self.completedCheckBox, 3, 3, 1, 1 )

        self.filenameLabel = QLabel( self )
        self.filenameLabel.setText( "File name:" )
        self.gridlayout.addWidget( self.filenameLabel, 4, 0, 1, 1 )

        self.filenameEdit = QLineEdit( self )
        self.filenameEdit.setFocusPolicy( Qt.NoFocus )
        self.filenameEdit.setReadOnly( True )
        self.gridlayout.addWidget( self.filenameEdit, 4, 1, 1, 3 )

        self.lineLabel = QLabel( self )
        self.lineLabel.setText( "Line:" )
        self.gridlayout.addWidget( self.lineLabel, 5, 0, 1, 1 )

        self.linenoEdit = QLineEdit( self )
        self.linenoEdit.setFocusPolicy( Qt.NoFocus )
        self.linenoEdit.setReadOnly( True )
        self.gridlayout.addWidget( self.linenoEdit, 5, 1, 1, 3 )

        self.buttonBox = QDialogButtonBox( self )
        self.buttonBox.setOrientation( Qt.Horizontal )
        self.buttonBox.setStandardButtons( QDialogButtonBox.Cancel | \
                                           QDialogButtonBox.Ok )
        self.gridlayout.addWidget( self.buttonBox, 6, 0, 1, 4 )

        self.descriptionLabel.setBuddy( self.descriptionEdit )

        self.buttonBox.accepted.connect( self.accept )
        self.buttonBox.rejected.connect( self.reject )
        QMetaObject.connectSlotsByName( self )
        self.setTabOrder( self.completedCheckBox, self.buttonBox )
        return

    def setReadOnly( self ):
        """ Disables editing some fields """

        self.descriptionEdit.setReadOnly( True )
        self.completedCheckBox.setEnabled( False )
        return

    def getData( self ):
        """ Provides the dialog data """

        return ( self.descriptionEdit.text(),
                 self.completedCheckBox.isChecked() )

