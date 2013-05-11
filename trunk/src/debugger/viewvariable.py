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
                          QLabel, QGridLayout, QSpinBox, QCheckBox,
                          QTextEdit )
from utils.pixmapcache import PixmapCache
from ui.combobox import CDMComboBox
from breakpoint import Breakpoint



class ViewVariableDialog( QDialog ):
    " Dialog all the properties of a variable "

    def __init__( self, varName, varType, varValue, parent = None ):
        QDialog.__init__( self, parent )
        self.__createLayout( varName, varType, varValue )
        return

    def __createLayout( self, varName, varType, varValue ):
        """ Creates the dialog layout """

        self.resize( 400, 150 )
        self.setSizeGripEnabled( True )

        # Top level layout
        layout = QVBoxLayout( self )

        gridLayout = QGridLayout()
        varNameLabel = QLabel( "Name:" )
        gridLayout.addWidget( varNameLabel, 0, 0 )
        varNameValue = QLabel( varName )
        gridLayout.addWidget( varNameValue, 0, 1 )
        varTypeLabel = QLabel( "Type:" )
        gridLayout.addWidget( varTypeLabel, 1, 0 )
        varTypeValue = QLabel( varType )
        gridLayout.addWidget( varTypeValue, 1, 1 )
        varValueLabel = QLabel( "Value:" )
        gridLayout.addWidget( varValueLabel, 2, 0 )
        varValueValue = QTextEdit()
        varValueValue.setReadOnly( True )
        gridLayout.addWidget( varValueValue, 2, 1 )
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

        self.__OKButton.setFocus()
        return

