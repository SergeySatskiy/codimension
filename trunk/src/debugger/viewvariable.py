#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2012  Sergey Satskiy <sergey.satskiy@gmail.com>
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


""" Dialog to show a single variable """


from PyQt4.QtCore import Qt, SIGNAL
from PyQt4.QtGui import ( QDialog, QDialogButtonBox, QVBoxLayout,
                          QLabel, QGridLayout, QTextEdit )
from utils.pixmapcache import PixmapCache
from ui.fitlabel import FramedLabelWithDoubleClick



class ViewVariableDialog( QDialog ):
    " Dialog all the properties of a variable "

    def __init__( self, nameLabel, varName,
                        varType, varValue, isGlobal, parent = None ):
        QDialog.__init__( self, parent )
        if isGlobal:
            self.setWindowTitle( "Global variable '" + varName + "'" )
            self.setWindowIcon( PixmapCache().getIcon( "globvar.png" ) )
        else:
            self.setWindowTitle( "Local variable '" + varName + "'" )
            self.setWindowIcon( PixmapCache().getIcon( "locvar.png" ) )
        self.__createLayout( nameLabel, varName, varType, varValue, isGlobal )
        return

    def __createLayout( self, nameLabel, varName, varType, varValue, isGlobal ):
        """ Creates the dialog layout """

        self.resize( 600, 250 )
        self.setSizeGripEnabled( True )

        # Top level layout
        layout = QVBoxLayout( self )

        gridLayout = QGridLayout()
        gridLayout.setSpacing( 2 )
        varScopeLabel = ( "Scope:" )
        gridLayout.addWidget( varScopeLabel, 0, 0, Qt.AlignTop )
        if isGlobal:
            varScopeValue = FramedLabelWithDoubleClick( "Global" )
        else:
            varScopeValue = FramedLabelWithDoubleClick( "Local" )
        varScopeValue.setToolTip( "Double click to copy" )
        gridLayout.addWidget( varScopeValue, 0, 1 )

        varNameLabel = QLabel( nameLabel + ":" )
        gridLayout.addWidget( varNameLabel, 1, 0, Qt.AlignTop )
        varNameValue = FramedLabelWithDoubleClick( varName )
        varNameValue.setToolTip( "Double click to copy" )
        font = varNameValue.font()
        font.setFamily( "Monospace" )
        varNameValue.setFont( font )
        gridLayout.addWidget( varNameValue, 1, 1 )
        varTypeLabel = QLabel( "Type:" )
        gridLayout.addWidget( varTypeLabel, 2, 0, Qt.AlignTop )
        varTypeValue = FramedLabelWithDoubleClick( varType )
        varTypeValue.setToolTip( "Double click to copy" )
        varTypeValue.setFont( font )
        gridLayout.addWidget( varTypeValue, 2, 1 )
        varValueLabel = QLabel( "Value:" )
        gridLayout.addWidget( varValueLabel, 3, 0, Qt.AlignTop )
        varValueValue = QTextEdit()
        varValueValue.setReadOnly( True )
        varValueValue.setFontFamily( "Monospace" )
        # varValueValue.setLineWrapMode( QTextEdit.NoWrap )
        varValueValue.setAcceptRichText( False )
        varValueValue.setPlainText( varValue )
        gridLayout.addWidget( varValueValue, 3, 1 )
        layout.addLayout( gridLayout )

        # Buttons at the bottom
        buttonBox = QDialogButtonBox( self )
        buttonBox.setOrientation( Qt.Horizontal )
        buttonBox.setStandardButtons( QDialogButtonBox.Ok )
        self.__OKButton = buttonBox.button( QDialogButtonBox.Ok )
        self.__OKButton.setDefault( True )
        self.connect( buttonBox, SIGNAL( "accepted()" ), self.close )
        self.connect( buttonBox, SIGNAL( "rejected()" ), self.close )
        layout.addWidget( buttonBox )

        varValueValue.setFocus()
        return

