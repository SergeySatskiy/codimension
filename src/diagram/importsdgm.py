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


""" imports diagram dialog """


import os, os.path
from PyQt4.QtCore                import Qt, SIGNAL
from PyQt4.QtGui                 import QDialog, QDialogButtonBox, \
                                        QVBoxLayout, QCheckBox




class ImportsDiagramDialog( QDialog, object ):
    """ Imports diagram properties dialog implementation """

    # Options of providing a diagram
    SingleFile     = 0
    DirectoryFiles = 1
    ProjectFiles   = 2
    SingleBuffer   = 3

    def __init__( self, option, path = "", parent = None ):

        QDialog.__init__( self, parent )

        self.__cancelRequest = False
        self.__inProgress = False
        self.__option = option
        self.__path = path

        # Avoid pylint complains
        self.includeClassesBox = None
        self.includeFuncsBox = None
        self.includeGlobsBox = None
        self.includeDocsBox = None
        self.includeConnTextBox = None

        self.__createLayout()
        title = "Imports diagram settings for "
        if self.__option == self.SingleFile:
            title += os.path.basename( self.__path )
        elif self.__option == self.DirectoryFiles:
            title += "directory " + self.__path
        elif self.__option == self.ProjectFiles:
            title += "the whole project"
        else:
            title += "modified file " + os.path.basename( self.__path )
        self.setWindowTitle( title )
        return

    def __createLayout( self ):
        """ Creates the dialog layout """

        self.resize( 400, 100 )
        self.setSizeGripEnabled( True )

        verticalLayout = QVBoxLayout( self )

        # Check boxes
        self.includeClassesBox = QCheckBox( self )
        self.includeClassesBox.setText( "Show &classes in modules" )
        self.includeClassesBox.setChecked( True )
        self.includeFuncsBox = QCheckBox( self )
        self.includeFuncsBox.setText( "Show &functions in modules" )
        self.includeFuncsBox.setChecked( True )
        self.includeGlobsBox = QCheckBox( self )
        self.includeGlobsBox.setText( "Show &global variables in modules" )
        self.includeGlobsBox.setChecked( True )
        self.includeDocsBox = QCheckBox( self )
        self.includeDocsBox.setText( "Show modules &docstrings" )
        self.includeDocsBox.setChecked( True )
        self.includeConnTextBox = QCheckBox( self )
        self.includeConnTextBox.setText( "Show connection &labels" )
        self.includeConnTextBox.setChecked( True )

        verticalLayout.addWidget( self.includeClassesBox )
        verticalLayout.addWidget( self.includeFuncsBox )
        verticalLayout.addWidget( self.includeGlobsBox )
        verticalLayout.addWidget( self.includeDocsBox )
        verticalLayout.addWidget( self.includeConnTextBox )

        # Buttons at the bottom
        buttonBox = QDialogButtonBox( self )
        buttonBox.setOrientation( Qt.Horizontal )
        buttonBox.setStandardButtons( QDialogButtonBox.Cancel )
        generateButton = buttonBox.addButton( "Generate",
                                              QDialogButtonBox.ActionRole )
        generateButton.setDefault( True )
        self.connect( generateButton, SIGNAL( 'clicked()' ), self.accept )
        verticalLayout.addWidget( buttonBox )

        self.connect( buttonBox, SIGNAL( "rejected()" ), self.close )
        return


