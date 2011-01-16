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


""" python code parser errors dialog """


import os, os.path
from PyQt4.QtCore       import Qt, SIGNAL
from PyQt4.QtGui        import QDialog, QTextEdit, QDialogButtonBox, \
                               QVBoxLayout, QSizePolicy
from fitlabel           import FitLabel
from utils.globals      import GlobalData
from utils.fileutils    import detectFileType, PythonFileType, Python3FileType



class ParserErrorsDialog( QDialog, object ):
    " python code parser errors dialog implementation "

    def __init__( self, fileName, parent = None ):

        QDialog.__init__( self, parent )

        if not os.path.exists( fileName ):
            raise Exception( "Cannot open " + fileName )

        if not detectFileType( fileName ) in [ PythonFileType,
                                               Python3FileType ]:
            raise Exception( "Unexpected file type (" + fileName + \
                             "). A python file is expected." )

        self.__createLayout( fileName )
        self.setWindowTitle( "Parser/lexer errors: " + \
                             os.path.basename( fileName ) )
        self.show()
        return

    def __createLayout( self, fileName ):
        """ Creates the dialog layout """

        self.resize( 600, 220 )
        self.setSizeGripEnabled( True )

        verticalLayout = QVBoxLayout( self )

        # Info label
        infoLabel = FitLabel( self )
        sizePolicy = QSizePolicy( QSizePolicy.Minimum, QSizePolicy.Preferred )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth(infoLabel.sizePolicy().hasHeightForWidth())
        infoLabel.setSizePolicy( sizePolicy )
        infoLabel.setText( "Parser/lexer errors for " + fileName )
        verticalLayout.addWidget( infoLabel )

        # Result window
        resultEdit = QTextEdit( self )
        resultEdit.setTabChangesFocus( False )
        resultEdit.setAcceptRichText( False )
        resultEdit.setReadOnly( True )
        resultEdit.setFontFamily( "Monospace" )
        resultEdit.setFontPointSize( 12.0 )
        if GlobalData().project.isProjectFile( fileName ):
            modInfo = GlobalData().project.briefModinfoCache.get( fileName )
        else:
            modInfo = GlobalData().briefModinfoCache.get( fileName )
        if len( modInfo.errors ) == 0:
            resultEdit.setText( "No errors found" )
        else:
            resultEdit.setText( "\n".join( modInfo.errors ) )
        verticalLayout.addWidget( resultEdit )

        # Buttons
        buttonBox = QDialogButtonBox( self )
        buttonBox.setOrientation( Qt.Horizontal )
        buttonBox.setStandardButtons( QDialogButtonBox.Close )
        verticalLayout.addWidget( buttonBox )

        self.connect( buttonBox, SIGNAL( "rejected()" ), self.close )
        return

